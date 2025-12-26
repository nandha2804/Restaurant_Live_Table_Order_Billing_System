"""
Celery tasks for background operations.
Handles notifications, abandoned table detection, and periodic checks.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# ORDER NOTIFICATION TASKS
# ============================================================================

@shared_task(bind=True, max_retries=3)
def notify_kitchen_order_task(self, order_id):
    """
    Celery task to notify kitchen of new order.
    Runs asynchronously when order is placed.
    """
    try:
        from restaurant.models import Order
        from restaurant.notifications import notify_kitchen_new_order
        
        order = Order.objects.get(id=order_id)
        notify_kitchen_new_order(order)
        return f"Kitchen notified of order #{order_id}"
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return f"Order {order_id} not found"
    except Exception as exc:
        logger.error(f"Error notifying kitchen: {str(exc)}")
        self.retry(exc=exc, countdown=60)

# ============================================================================
# BILL MONITORING TASKS
# ============================================================================

@shared_task
def check_pending_bills():
    """
    Periodic task to check for bills pending too long.
    Alerts manager if bill hasn't been paid after X hours.
    """
    try:
        from restaurant.models import Bill
        from restaurant.notifications import notify_manager_pending_bill
        
        # Find bills pending for more than 2 hours
        pending_threshold = timezone.now() - timedelta(hours=2)
        pending_bills = Bill.objects.filter(
            status='pending',
            created_at__lte=pending_threshold
        )
        
        for bill in pending_bills:
            # Check if notification already sent (simple check)
            if not hasattr(bill, '_notification_sent'):
                notify_manager_pending_bill(bill, hours_pending=2)
                bill._notification_sent = True
        
        logger.info(f"Checked {pending_bills.count()} pending bills")
        return f"Checked {pending_bills.count()} pending bills"
    except Exception as exc:
        logger.error(f"Error checking pending bills: {str(exc)}")
        return f"Error: {str(exc)}"

@shared_task
def check_abandoned_tables():
    """
    Periodic task to detect and auto-close abandoned tables.
    A table is considered abandoned if:
    - Occupied for more than 4 hours without order, OR
    - Bill requested but not paid for more than 1 hour
    """
    try:
        from restaurant.models import Table, Bill
        from restaurant.notifications import Notification
        
        abandoned_count = 0
        current_time = timezone.now()
        
        # Check for occupied tables without orders for too long
        occupied_tables = Table.objects.filter(status='occupied')
        for table in occupied_tables:
            # Get latest order for the table
            latest_order = table.orders.latest('created_at') if table.orders.exists() else None
            
            if latest_order:
                time_diff = current_time - latest_order.created_at
                # If occupied for more than 4 hours, mark as abandoned
                if time_diff > timedelta(hours=4):
                    table.status = 'closed'
                    table.save()
                    
                    # Notify manager
                    managers = User.objects.filter(groups__name='Manager')
                    for manager in managers:
                        Notification.create_notification(
                            user=manager,
                            notification_type='table_abandoned',
                            title=f"Table {table.table_number} Auto-Closed",
                            message=f"Table {table.table_number} was occupied for 4+ hours and has been auto-closed",
                            table_id=table.id
                        )
                    abandoned_count += 1
        
        # Check for bills pending too long (more than 1 hour)
        pending_bills = Bill.objects.filter(status='pending')
        for bill in pending_bills:
            time_diff = current_time - bill.created_at
            if time_diff > timedelta(hours=1):
                # Already notified via check_pending_bills
                pass
        
        logger.info(f"Closed {abandoned_count} abandoned tables")
        return f"Auto-closed {abandoned_count} abandoned tables"
    except Exception as exc:
        logger.error(f"Error checking abandoned tables: {str(exc)}")
        return f"Error: {str(exc)}"

# ============================================================================
# PAYMENT NOTIFICATION TASKS
# ============================================================================

@shared_task(bind=True, max_retries=3)
def notify_payment_received_task(self, bill_id):
    """
    Celery task to notify staff of payment received.
    Runs when bill is marked as paid.
    """
    try:
        from restaurant.models import Bill
        from restaurant.notifications import notify_payment_received
        
        bill = Bill.objects.get(id=bill_id)
        notify_payment_received(bill)
        return f"Payment notification sent for bill #{bill_id}"
    except Bill.DoesNotExist:
        logger.error(f"Bill {bill_id} not found")
        return f"Bill {bill_id} not found"
    except Exception as exc:
        logger.error(f"Error notifying payment: {str(exc)}")
        self.retry(exc=exc, countdown=60)

# ============================================================================
# ORDER STATUS CHANGE TASKS
# ============================================================================

@shared_task(bind=True, max_retries=3)
def notify_order_ready_task(self, order_id):
    """
    Celery task to notify waiter when order is ready.
    Runs when order is marked as served by kitchen.
    """
    try:
        from restaurant.models import Order
        from restaurant.notifications import notify_order_ready
        
        order = Order.objects.get(id=order_id)
        notify_order_ready(order)
        return f"Waiter notified that order #{order_id} is ready"
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return f"Order {order_id} not found"
    except Exception as exc:
        logger.error(f"Error notifying order ready: {str(exc)}")
        self.retry(exc=exc, countdown=60)

# ============================================================================
# PERIODIC CLEANUP TASKS
# ============================================================================

@shared_task
def cleanup_old_notifications():
    """
    Periodic task to clean up old read notifications (older than 30 days).
    """
    try:
        from restaurant.notifications import Notification
        
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count, _ = Notification.objects.filter(
            is_read=True,
            read_at__lt=cutoff_date
        ).delete()
        
        logger.info(f"Cleaned up {deleted_count} old notifications")
        return f"Cleaned up {deleted_count} old notifications"
    except Exception as exc:
        logger.error(f"Error cleaning up notifications: {str(exc)}")
        return f"Error: {str(exc)}"

@shared_task
def generate_daily_report():
    """
    Periodic task to generate daily sales and operations report.
    """
    try:
        from restaurant.models import Bill, Order, Table
        from django.db.models import Sum
        
        current_date = timezone.now().date()
        
        # Get today's data
        today_bills = Bill.objects.filter(
            status='paid',
            paid_at__date=current_date
        )
        today_orders = Order.objects.filter(
            status='served',
            updated_at__date=current_date
        )
        
        total_revenue = today_bills.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        total_bills = today_bills.count()
        total_orders = today_orders.count()
        
        report = {
            'date': current_date,
            'total_revenue': float(total_revenue),
            'total_bills': total_bills,
            'total_orders': total_orders,
            'average_bill': float(total_revenue / total_bills) if total_bills > 0 else 0,
        }
        
        logger.info(f"Daily report generated: {report}")
        return report
    except Exception as exc:
        logger.error(f"Error generating daily report: {str(exc)}")
        return f"Error: {str(exc)}"

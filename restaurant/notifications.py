"""
Notifications system for restaurant operations.
Handles in-app notifications and background task alerts.
"""
from django.contrib.auth.models import User
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# NOTIFICATION HELPER FUNCTIONS
# ============================================================================

def notify_kitchen_new_order(order):
    """
    Notify kitchen staff when a new order is placed.
    Sends notification to all users in 'Kitchen' group.
    """
    from restaurant.models import Notification
    
    try:
        # Get all kitchen staff (or managers who can see kitchen orders)
        kitchen_staff = User.objects.filter(groups__name__in=['Manager', 'Kitchen'])
        
        title = f"New Order #{order.id} - Table {order.table.table_number}"
        message = f"Order placed for Table {order.table.table_number} with {order.items.count()} items"
        
        for user in kitchen_staff:
            Notification.objects.create(
                user=user,
                notification_type='order_placed',
                title=title,
                message=message,
                table_id=order.table.id,
                order_id=order.id
            )
        
        logger.info(f"Kitchen notified of new order #{order.id}")
    except Exception as e:
        logger.error(f"Error notifying kitchen: {str(e)}")

def notify_manager_pending_bill(bill, hours_pending=2):
    """
    Notify manager when a bill remains unpaid for X hours.
    """
    from restaurant.models import Notification
    
    try:
        # Get all managers
        managers = User.objects.filter(groups__name='Manager')
        
        title = f"Bill #{bill.id} Pending Payment - Table {bill.table.table_number}"
        message = f"Bill for Table {bill.table.table_number} (₹{bill.total_amount}) has been pending for {hours_pending} hours"
        
        for manager in managers:
            Notification.objects.create(
                user=manager,
                notification_type='bill_pending',
                title=title,
                message=message,
                table_id=bill.table.id,
                bill_id=bill.id
            )
        
        logger.info(f"Manager notified about pending bill #{bill.id}")
    except Exception as e:
        logger.error(f"Error notifying manager: {str(e)}")

def notify_order_ready(order):
    """
    Notify waiter when order is ready to be served.
    """
    from restaurant.models import Notification
    
    try:
        # Notify the waiter/manager assigned to the table
        waiters = User.objects.filter(groups__name__in=['Waiter', 'Manager'])
        
        title = f"Order #{order.id} Ready - Table {order.table.table_number}"
        message = f"Order for Table {order.table.table_number} is ready to be served"
        
        for user in waiters:
            Notification.objects.create(
                user=user,
                notification_type='order_ready',
                title=title,
                message=message,
                table_id=order.table.id,
                order_id=order.id
            )
        
        logger.info(f"Waiters notified that order #{order.id} is ready")
    except Exception as e:
        logger.error(f"Error notifying order ready: {str(e)}")

def notify_payment_received(bill):
    """
    Notify relevant staff when payment is received.
    """
    from restaurant.models import Notification
    
    try:
        staff = User.objects.filter(groups__name__in=['Cashier', 'Manager'])
        
        title = f"Payment Received - Table {bill.table.table_number}"
        message = f"Bill #{bill.id} for Table {bill.table.table_number} (₹{bill.total_amount}) paid successfully"
        
        for user in staff:
            Notification.objects.create(
                user=user,
                notification_type='payment_received',
                title=title,
                message=message,
                table_id=bill.table.id,
                bill_id=bill.id
            )
        
        logger.info(f"Staff notified about payment for bill #{bill.id}")
    except Exception as e:
        logger.error(f"Error notifying payment: {str(e)}")

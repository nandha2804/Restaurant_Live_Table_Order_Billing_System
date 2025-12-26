from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .models import Table, MenuItem, Order, OrderItem, Bill
from decimal import Decimal

# ============================================================================
# HOME VIEW
# ============================================================================

def home(request):
    """Home page view - accessible to all users."""
    return render(request, 'home.html')

# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

def login_view(request):
    """User login view."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            
            # Redirect based on role
            user_role = user.groups.all().first()
            if user_role:
                if user_role.name == 'Waiter':
                    return redirect('orders')
                elif user_role.name == 'Cashier':
                    return redirect('billing')
                elif user_role.name == 'Manager':
                    return redirect('dashboard')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials')
    
    return render(request, 'auth/login.html')

@login_required
def logout_view(request):
    """User logout view."""
    logout(request)
    messages.success(request, 'You have been logged out')
    return redirect('login')

# ============================================================================
# DASHBOARD VIEWS
# ============================================================================

@login_required
def dashboard(request):
    """Main dashboard showing table overview."""
    tables = Table.objects.all()
    occupied_tables = tables.filter(status='occupied').count()
    available_tables = tables.filter(status='available').count()
    bill_requested = tables.filter(status='bill_requested').count()
    
    recent_bills = Bill.objects.filter(status='paid').order_by('-paid_at')[:5]
    total_revenue = sum(bill.total_amount for bill in recent_bills)
    
    context = {
        'tables': tables,
        'occupied_tables': occupied_tables,
        'available_tables': available_tables,
        'bill_requested': bill_requested,
        'recent_bills': recent_bills,
        'total_revenue': total_revenue,
    }
    return render(request, 'dashboard/tables.html', context)

# ============================================================================
# WAITER VIEWS - ORDER MANAGEMENT
# ============================================================================

@login_required
def orders_list(request):
    """List all active orders."""
    if request.user.groups.filter(name='Waiter').exists() or request.user.groups.filter(name='Manager').exists():
        orders = Order.objects.filter(status__in=['placed', 'in_kitchen', 'served']).order_by('-created_at')
        menu_items = MenuItem.objects.filter(is_available=True)
        
        context = {
            'orders': orders,
            'menu_items': menu_items,
        }
        return render(request, 'orders/orders_list.html', context)
    else:
        messages.error(request, 'You do not have permission to view orders')
        return redirect('dashboard')

@login_required
@require_http_methods(['GET', 'POST'])
def create_order(request):
    """Create new order for a table."""
    if not request.user.groups.filter(name__in=['Waiter', 'Manager']).exists():
        messages.error(request, 'You do not have permission to create orders')
        return redirect('dashboard')
    
    tables = Table.objects.filter(status__in=['available', 'occupied'])
    menu_items = MenuItem.objects.filter(is_available=True)
    
    if request.method == 'POST':
        table_id = request.POST.get('table')
        table = get_object_or_404(Table, id=table_id)
        
        if table.status != 'available':
            messages.error(request, f'Table {table.table_number} is not available')
            return redirect('orders')
        
        order = Order.objects.create(table=table)
        table.mark_occupied()
        
        # Add items to order
        for key, value in request.POST.items():
            if key.startswith('quantity_'):
                item_id = key.replace('quantity_', '')
                quantity = int(value) if value else 0
                
                if quantity > 0:
                    menu_item = MenuItem.objects.get(id=item_id)
                    OrderItem.objects.create(
                        order=order,
                        menu_item=menu_item,
                        quantity=quantity
                    )
        
        # Trigger notification task
        try:
            from restaurant.tasks import notify_kitchen_order_task
            notify_kitchen_order_task.delay(order.id)
        except Exception as e:
            pass  # Continue even if task fails
        
        messages.success(request, f'Order #{order.id} created successfully')
        return redirect('order-detail', order_id=order.id)
    
    context = {
        'tables': tables,
        'menu_items': menu_items,
    }
    return render(request, 'orders/create_order.html', context)

@login_required
def order_detail(request, order_id):
    """View order details."""
    order = get_object_or_404(Order, id=order_id)
    items = order.items.all()
    subtotal = order.calculate_subtotal()
    tax_amount = subtotal * Decimal('0.05')
    total = subtotal + tax_amount
    
    context = {
        'order': order,
        'items': items,
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'total': total,
    }
    return render(request, 'orders/order_detail.html', context)

@login_required
@require_http_methods(['POST'])
def send_to_kitchen(request, order_id):
    """Send order to kitchen."""
    order = get_object_or_404(Order, id=order_id)
    
    if order.status == 'placed':
        order.send_to_kitchen()
        messages.success(request, 'Order sent to kitchen')
    
    return redirect('order-detail', order_id=order.id)

@login_required
@require_http_methods(['POST'])
def mark_served(request, order_id):
    """Mark order as served."""
    order = get_object_or_404(Order, id=order_id)
    
    if order.status == 'in_kitchen':
        order.mark_served()
        messages.success(request, 'Order marked as served')
    
    return redirect('order-detail', order_id=order.id)

# ============================================================================
# CASHIER VIEWS - BILLING
# ============================================================================

@login_required
def billing_dashboard(request):
    """Billing dashboard for cashiers."""
    if not request.user.groups.filter(name__in=['Cashier', 'Manager']).exists():
        messages.error(request, 'You do not have permission to view billing')
        return redirect('dashboard')
    
    pending_bills = Bill.objects.filter(status='pending').order_by('-created_at')
    paid_bills = Bill.objects.filter(status='paid').order_by('-paid_at')[:10]
    
    total_pending = sum(bill.total_amount for bill in pending_bills)
    total_paid_today = sum(bill.total_amount for bill in paid_bills)
    
    context = {
        'pending_bills': pending_bills,
        'paid_bills': paid_bills,
        'total_pending': total_pending,
        'total_paid_today': total_paid_today,
    }
    return render(request, 'billing/billing_dashboard.html', context)

@login_required
def generate_bill(request, table_id):
    """Generate bill for a table."""
    if not request.user.groups.filter(name__in=['Cashier', 'Manager']).exists():
        messages.error(request, 'You do not have permission to generate bills')
        return redirect('dashboard')
    
    table = get_object_or_404(Table, id=table_id)
    table.request_bill()
    
    # Get latest order for table
    order = table.orders.filter(status='served').order_by('-created_at').first()
    
    if order:
        bill, created = Bill.objects.get_or_create(table=table)
        bill.generate_bill(order)
        messages.success(request, f'Bill generated for Table {table.table_number}')
        return redirect('bill-detail', bill_id=bill.id)
    else:
        messages.error(request, 'No served orders found for this table')
        return redirect('billing')

@login_required
def bill_detail(request, bill_id):
    """View bill details."""
    bill = get_object_or_404(Bill, id=bill_id)
    
    context = {
        'bill': bill,
        'items': bill.order.items.all() if bill.order else [],
    }
    return render(request, 'billing/bill_detail.html', context)

@login_required
@require_http_methods(['POST'])
def mark_paid(request, bill_id):
    """Mark bill as paid."""
    bill = get_object_or_404(Bill, id=bill_id)
    
    if bill.status == 'pending':
        bill.mark_as_paid()
        
        # Trigger notification task
        try:
            from restaurant.tasks import notify_payment_received_task
            notify_payment_received_task.delay(bill.id)
        except Exception as e:
            pass  # Continue even if task fails
        
        messages.success(request, 'Bill marked as paid. Table reset to available.')
    
    return redirect('billing')

# ============================================================================
# MANAGER VIEWS - MENU & TABLE MANAGEMENT
# ============================================================================

@login_required
def menu_list(request):
    """List all menu items."""
    if not request.user.groups.filter(name='Manager').exists():
        messages.error(request, 'You do not have permission to view menu')
        return redirect('dashboard')
    
    menu_items = MenuItem.objects.all().order_by('category', 'name')
    
    context = {
        'menu_items': menu_items,
        'categories': MenuItem.objects.values_list('category', flat=True).distinct(),
    }
    return render(request, 'manager/menu_list.html', context)

@login_required
def table_list(request):
    """List all tables."""
    if not request.user.groups.filter(name='Manager').exists():
        messages.error(request, 'You do not have permission to view tables')
        return redirect('dashboard')
    
    tables = Table.objects.all().order_by('table_number')
    
    context = {
        'tables': tables,
    }
    return render(request, 'manager/table_list.html', context)

@login_required
def reports(request):
    """View reports and analytics."""
    if not request.user.groups.filter(name='Manager').exists():
        messages.error(request, 'You do not have permission to view reports')
        return redirect('dashboard')
    
    all_bills = Bill.objects.filter(status='paid')
    total_revenue = sum(bill.total_amount for bill in all_bills)
    total_bills = all_bills.count()
    total_tax = sum(bill.tax_amount for bill in all_bills)
    
    tables = Table.objects.all()
    table_usage = {
        'available': tables.filter(status='available').count(),
        'occupied': tables.filter(status='occupied').count(),
        'bill_requested': tables.filter(status='bill_requested').count(),
        'closed': tables.filter(status='closed').count(),
    }
    
    context = {
        'total_revenue': total_revenue,
        'total_bills': total_bills,
        'total_tax': total_tax,
        'average_bill': total_revenue / total_bills if total_bills > 0 else 0,
        'table_usage': table_usage,
    }
    return render(request, 'manager/reports.html', context)

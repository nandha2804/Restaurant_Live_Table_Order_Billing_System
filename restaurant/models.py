from django.db import models
from django.contrib.auth.models import User, Group
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal

# ============================================================================
# TABLE MANAGEMENT
# ============================================================================

class Table(models.Model):
    """
    Restaurant table model with status tracking.
    Status flow: Available -> Occupied -> Bill Requested -> Closed -> Available
    """
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('bill_requested', 'Bill Requested'),
        ('closed', 'Closed'),
    ]

    table_number = models.IntegerField(unique=True)
    seating_capacity = models.IntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['table_number']
        verbose_name_plural = 'Tables'

    def __str__(self):
        return f"Table {self.table_number} ({self.get_status_display()})"

    def mark_occupied(self):
        """Mark table as occupied when order is placed."""
        if self.status == 'available':
            self.status = 'occupied'
            self.save()

    def request_bill(self):
        """Mark table as bill requested."""
        self.status = 'bill_requested'
        self.save()

    def reset_to_available(self):
        """Reset table to available after payment."""
        self.status = 'available'
        self.save()


# ============================================================================
# MENU MANAGEMENT
# ============================================================================

class MenuItem(models.Model):
    """Menu items available in the restaurant."""
    CATEGORY_CHOICES = [
        ('starter', 'Starter'),
        ('main', 'Main'),
        ('drinks', 'Drinks'),
        ('dessert', 'Dessert'),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    description = models.TextField(blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} - ₹{self.price}"


# ============================================================================
# ORDER MANAGEMENT
# ============================================================================

class Order(models.Model):
    """Order placed for a table."""
    STATUS_CHOICES = [
        ('placed', 'Placed'),
        ('in_kitchen', 'In Kitchen'),
        ('served', 'Served'),
        ('cancelled', 'Cancelled'),
    ]

    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='placed'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - Table {self.table.table_number}"

    def calculate_subtotal(self):
        """Calculate subtotal from order items."""
        return sum(item.get_total_price() for item in self.items.all())

    def send_to_kitchen(self):
        """Move order to kitchen."""
        if self.status == 'placed':
            self.status = 'in_kitchen'
            self.save()

    def mark_served(self):
        """Mark order as served."""
        if self.status == 'in_kitchen':
            self.status = 'served'
            self.save()


class OrderItem(models.Model):
    """Individual item in an order."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    special_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('order', 'menu_item')

    def __str__(self):
        return f"{self.menu_item.name} x{self.quantity}"

    def get_total_price(self):
        """Get total price for this order item."""
        return self.menu_item.price * self.quantity


# ============================================================================
# BILLING MANAGEMENT
# ============================================================================

class Bill(models.Model):
    """Bill for a table."""
    BILL_STATUS_CHOICES = [
        ('not_generated', 'Not Generated'),
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    table = models.OneToOneField(Table, on_delete=models.CASCADE, related_name='bill')
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='bill', null=True, blank=True)
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text="Tax percentage to apply"
    )
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    status = models.CharField(
        max_length=20,
        choices=BILL_STATUS_CHOICES,
        default='not_generated'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Bill for Table {self.table.table_number} - ₹{self.total_amount}"

    def generate_bill(self, order):
        """Generate bill from order."""
        self.order = order
        self.subtotal = order.calculate_subtotal()
        self.tax_amount = (self.subtotal * self.tax_percentage) / Decimal('100')
        self.total_amount = self.subtotal + self.tax_amount
        self.status = 'pending'
        self.save()

    def mark_as_paid(self):
        """Mark bill as paid and reset table."""
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.save()
        
        # Reset table to available
        self.table.reset_to_available()


# ============================================================================
# USER ROLES & PERMISSIONS (using Django Groups)
# ============================================================================

# ============================================================================
# NOTIFICATIONS
# ============================================================================

class Notification(models.Model):
    """In-app notifications for users."""
    NOTIFICATION_TYPES = [
        ('order_placed', 'Order Placed'),
        ('order_ready', 'Order Ready'),
        ('bill_pending', 'Bill Pending'),
        ('table_abandoned', 'Table Abandoned'),
        ('order_cancelled', 'Order Cancelled'),
        ('payment_received', 'Payment Received'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    table_id = models.IntegerField(null=True, blank=True)
    order_id = models.IntegerField(null=True, blank=True)
    bill_id = models.IntegerField(null=True, blank=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    def mark_as_read(self):
        """Mark notification as read."""
        self.is_read = True
        self.read_at = timezone.now()
        self.save()

# ============================================================================
# USER ROLES & PERMISSIONS (using Django Groups)
# ============================================================================

def create_user_roles():
    """Create default user roles/groups."""
    roles = {
        'Waiter': [
            'add_order', 'change_order', 'view_order',
            'add_orderitem', 'change_orderitem', 'view_orderitem',
            'view_table', 'view_menuitem', 'view_bill'
        ],
        'Cashier': [
            'add_bill', 'change_bill', 'view_bill',
            'view_order', 'view_orderitem',
            'view_table', 'view_menuitem'
        ],
        'Manager': [
            'add_table', 'change_table', 'view_table', 'delete_table',
            'add_menuitem', 'change_menuitem', 'view_menuitem', 'delete_menuitem',
            'add_order', 'change_order', 'view_order', 'delete_order',
            'add_orderitem', 'change_orderitem', 'view_orderitem', 'delete_orderitem',
            'add_bill', 'change_bill', 'view_bill', 'delete_bill',
            'add_user', 'change_user', 'view_user', 'delete_user'
        ]
    }
    
    for role_name, permissions in roles.items():
        group, created = Group.objects.get_or_create(name=role_name)
        if created:
            from django.contrib.auth.models import Permission
            from django.contrib.contenttypes.models import ContentType
            
            for perm_codename in permissions:
                try:
                    # Split the permission string
                    app_label = 'restaurant'
                    parts = perm_codename.split('_')
                    action = parts[0]
                    model = '_'.join(parts[1:])
                    
                    # Get the permission
                    permission = Permission.objects.get(
                        codename=perm_codename,
                        content_type__app_label=app_label
                    )
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    pass

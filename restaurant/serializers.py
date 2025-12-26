from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Table, MenuItem, Order, OrderItem, Bill


# ============================================================================
# USER SERIALIZERS
# ============================================================================

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    groups = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'groups', 'is_active']
        read_only_fields = ['id']


# ============================================================================
# TABLE SERIALIZERS
# ============================================================================

class TableSerializer(serializers.ModelSerializer):
    """Serializer for Table model."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Table
        fields = [
            'id', 'table_number', 'seating_capacity', 'status',
            'status_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_seating_capacity(self, value):
        if value < 1:
            raise serializers.ValidationError("Seating capacity must be at least 1.")
        return value


# ============================================================================
# MENU ITEM SERIALIZERS
# ============================================================================

class MenuItemSerializer(serializers.ModelSerializer):
    """Serializer for MenuItem model."""
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'category', 'category_display', 'price',
            'description', 'is_available', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value


# ============================================================================
# ORDER SERIALIZERS
# ============================================================================

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model."""
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_price = serializers.DecimalField(
        source='menu_item.price',
        read_only=True,
        max_digits=8,
        decimal_places=2
    )
    total_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'menu_item', 'menu_item_name', 'menu_item_price',
            'quantity', 'total_price', 'special_notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_total_price(self, obj):
        return obj.get_total_price()

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value

    def validate(self, data):
        """Validate that menu item is available."""
        menu_item = data.get('menu_item')
        if menu_item and not menu_item.is_available:
            raise serializers.ValidationError({
                'menu_item': f'Menu item "{menu_item.name}" is not available.'
            })
        return data


class OrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for Order list view."""
    table_number = serializers.IntegerField(source='table.table_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'table', 'table_number', 'status', 'status_display',
            'items_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_items_count(self, obj):
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Order with items."""
    table_number = serializers.IntegerField(source='table.table_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'table', 'table_number', 'status', 'status_display',
            'items', 'subtotal', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_subtotal(self, obj):
        return obj.calculate_subtotal()


# ============================================================================
# BILL SERIALIZERS
# ============================================================================

class BillSerializer(serializers.ModelSerializer):
    """Serializer for Bill model."""
    table_number = serializers.IntegerField(source='table.table_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Bill
        fields = [
            'id', 'table', 'table_number', 'order',
            'subtotal', 'tax_percentage', 'tax_amount', 'total_amount',
            'status', 'status_display', 'created_at', 'updated_at', 'paid_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'paid_at']


class BillDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Bill with order items."""
    table_number = serializers.IntegerField(source='table.table_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    order_items = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Bill
        fields = [
            'id', 'table', 'table_number', 'order',
            'order_items',
            'subtotal', 'tax_percentage', 'tax_amount', 'total_amount',
            'status', 'status_display', 'created_at', 'updated_at', 'paid_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'paid_at']

    def get_order_items(self, obj):
        """Get all items from the order."""
        if obj.order:
            return OrderItemSerializer(obj.order.items.all(), many=True).data
        return []


# ============================================================================
# DASHBOARD SERIALIZERS
# ============================================================================

class DashboardTableSerializer(serializers.ModelSerializer):
    """Serializer for dashboard showing tables with their current state."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    current_order = serializers.SerializerMethodField(read_only=True)
    bill_status = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Table
        fields = [
            'id', 'table_number', 'seating_capacity', 'status', 'status_display',
            'current_order', 'bill_status', 'updated_at'
        ]

    def get_current_order(self, obj):
        """Get the most recent order for this table."""
        latest_order = obj.orders.filter(status__in=['placed', 'in_kitchen', 'served']).first()
        if latest_order:
            return OrderListSerializer(latest_order).data
        return None

    def get_bill_status(self, obj):
        """Get the bill status for this table."""
        try:
            bill = obj.bill
            return {
                'id': bill.id,
                'status': bill.status,
                'status_display': bill.get_status_display(),
                'total_amount': str(bill.total_amount)
            }
        except Bill.DoesNotExist:
            return None

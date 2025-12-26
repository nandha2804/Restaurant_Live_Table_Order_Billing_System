from django.contrib import admin
from .models import Table, MenuItem, Order, OrderItem, Bill

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['table_number', 'seating_capacity', 'status', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['table_number']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Table Information', {
            'fields': ('table_number', 'seating_capacity', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_available', 'updated_at']
    list_filter = ['category', 'is_available', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Menu Item Details', {
            'fields': ('name', 'category', 'price', 'description', 'is_available')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'table', 'status', 'created_at', 'items_count']
    list_filter = ['status', 'created_at']
    search_fields = ['table__table_number', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    
    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Items'

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'menu_item', 'quantity', 'get_total_price', 'created_at']
    list_filter = ['created_at', 'order__table']
    search_fields = ['menu_item__name', 'order__id']
    readonly_fields = ['created_at']

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['id', 'table', 'subtotal', 'tax_amount', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'paid_at']
    search_fields = ['table__table_number']
    readonly_fields = ['created_at', 'updated_at', 'paid_at']
    fieldsets = (
        ('Bill Details', {
            'fields': ('table', 'order', 'status')
        }),
        ('Amount Calculation', {
            'fields': ('subtotal', 'tax_percentage', 'tax_amount', 'total_amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'paid_at'),
            'classes': ('collapse',)
        }),
    )

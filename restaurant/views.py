from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User, Group
from django.db.models import Q, F
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import Table, MenuItem, Order, OrderItem, Bill
from .serializers import (
    UserSerializer, TableSerializer, MenuItemSerializer,
    OrderListSerializer, OrderDetailSerializer, OrderItemSerializer,
    BillSerializer, BillDetailSerializer, DashboardTableSerializer
)

# ============================================================================
# CUSTOM PERMISSIONS
# ============================================================================

class IsWaiter(permissions.BasePermission):
    """Permission for Waiter role."""
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name='Waiter').exists()

class IsCashier(permissions.BasePermission):
    """Permission for Cashier role."""
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name='Cashier').exists()

class IsManager(permissions.BasePermission):
    """Permission for Manager role."""
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name='Manager').exists()

class IsManagerOrReadOnly(permissions.BasePermission):
    """Manager can edit, others can only read."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.groups.filter(name='Manager').exists()

# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def obtain_token(request):
    """
    Get authentication token for a user.
    POST /api/auth/login/
    {
        "username": "waiter1",
        "password": "password123"
    }
    """
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': 'Username and password are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response(
            {'error': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.check_password(password):
        return Response(
            {'error': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    token, created = Token.objects.get_or_create(user=user)
    return Response({
        'token': token.key,
        'user': UserSerializer(user).data
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    """Logout and delete token."""
    if request.user.is_authenticated:
        request.user.auth_token.delete()
    return Response({'message': 'Logged out successfully.'})

# ============================================================================
# TABLE VIEWS
# ============================================================================

class TableViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Table management.
    Only Manager can create/edit/delete. Waiters can view and request bills.
    """
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    permission_classes = [IsAuthenticated, IsManagerOrReadOnly]

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def request_bill(self, request, pk=None):
        """Waiter requests a bill for a table."""
        table = self.get_object()

        if table.status == 'available':
            return Response(
                {'error': 'Cannot request bill for an available table.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        table.request_bill()
        return Response(
            {'message': 'Bill requested.', 'status': table.get_status_display()}
        )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def dashboard(self, request):
        """Get live dashboard of all tables."""
        tables = self.get_queryset()
        serializer = DashboardTableSerializer(tables, many=True)
        return Response(serializer.data)

# ============================================================================
# MENU ITEM VIEWS
# ============================================================================

class MenuItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Menu Item management.
    Only Manager can create/edit/delete. Others can view.
    """
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated, IsManagerOrReadOnly]
    filterset_fields = ['category', 'is_available']

# ============================================================================
# ORDER VIEWS
# ============================================================================

class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Order management.
    Waiters can create and update orders.
    """
    queryset = Order.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use different serializers for list and detail views."""
        if self.action == 'retrieve':
            return OrderDetailSerializer
        return OrderListSerializer

    def get_queryset(self):
        """Filter based on user role."""
        user = self.request.user
        if user.groups.filter(name='Manager').exists():
            return Order.objects.all()
        return Order.objects.all()

    def create(self, request, *args, **kwargs):
        """
        Create a new order for a table.
        POST /api/orders/
        {
            "table": 1,
            "notes": "Special instructions"
        }
        """
        table_id = request.data.get('table')

        if not table_id:
            return Response(
                {'error': 'Table ID is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            table = Table.objects.get(id=table_id)
        except Table.DoesNotExist:
            return Response(
                {'error': 'Table not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if table is available
        if table.status != 'available':
            return Response(
                {'error': f'Table is {table.get_status_display()}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create order
        order = Order.objects.create(
            table=table,
            notes=request.data.get('notes', '')
        )

        # Mark table as occupied
        table.mark_occupied()

        return Response(
            OrderDetailSerializer(order).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_item(self, request, pk=None):
        """
        Add an item to an order.
        POST /api/orders/{id}/add_item/
        {
            "menu_item": 1,
            "quantity": 2,
            "special_notes": "No onions"
        }
        """
        order = self.get_object()
        menu_item_id = request.data.get('menu_item')
        quantity = request.data.get('quantity')
        special_notes = request.data.get('special_notes', '')

        if not menu_item_id or not quantity:
            return Response(
                {'error': 'menu_item and quantity are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            menu_item = MenuItem.objects.get(id=menu_item_id)
        except MenuItem.DoesNotExist:
            return Response(
                {'error': 'Menu item not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not menu_item.is_available:
            return Response(
                {'error': f'"{menu_item.name}" is not available.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(quantity)
            if quantity < 1:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {'error': 'Quantity must be a positive integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create or update order item
        order_item, created = OrderItem.objects.update_or_create(
            order=order,
            menu_item=menu_item,
            defaults={'quantity': quantity, 'special_notes': special_notes}
        )

        return Response(
            {
                'message': 'Item added to order.',
                'order_item': OrderItemSerializer(order_item).data
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def send_to_kitchen(self, request, pk=None):
        """Send order to kitchen."""
        order = self.get_object()

        if not order.items.exists():
            return Response(
                {'error': 'Cannot send empty order to kitchen.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if order.status != 'placed':
            return Response(
                {'error': f'Order is already {order.get_status_display()}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.send_to_kitchen()
        return Response(
            {'message': 'Order sent to kitchen.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_served(self, request, pk=None):
        """Mark order as served."""
        order = self.get_object()

        if order.status != 'in_kitchen':
            return Response(
                {'error': f'Order is {order.get_status_display()}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.mark_served()
        return Response(
            {'message': 'Order marked as served.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def remove_item(self, request, pk=None):
        """
        Remove an item from order.
        DELETE /api/orders/{id}/remove_item/?item_id=1
        """
        order = self.get_object()
        item_id = request.query_params.get('item_id')

        if not item_id:
            return Response(
                {'error': 'item_id parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order_item = OrderItem.objects.get(id=item_id, order=order)
            order_item.delete()
            return Response({'message': 'Item removed from order.'})
        except OrderItem.DoesNotExist:
            return Response(
                {'error': 'Order item not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

# ============================================================================
# BILL VIEWS
# ============================================================================

class BillViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Bill management.
    Cashiers can generate and manage bills.
    """
    queryset = Bill.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use different serializers for list and detail views."""
        if self.action == 'retrieve':
            return BillDetailSerializer
        return BillSerializer

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def generate_bill(self, request, pk=None):
        """
        Generate a bill for a table.
        POST /api/bills/{id}/generate_bill/
        {
            "order": 1
        }
        """
        bill = self.get_object()
        order_id = request.data.get('order')

        if not order_id:
            return Response(
                {'error': 'order ID is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not order.items.exists():
            return Response(
                {'error': 'Cannot generate bill for order with no items.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        bill.generate_bill(order)
        bill.table.request_bill()

        return Response(
            BillDetailSerializer(bill).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_as_paid(self, request, pk=None):
        """
        Mark bill as paid and reset table.
        POST /api/bills/{id}/mark_as_paid/
        """
        bill = self.get_object()

        if bill.status == 'paid':
            return Response(
                {'error': 'Bill is already paid.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        bill.mark_as_paid()

        return Response(
            {
                'message': 'Bill marked as paid. Table reset to available.',
                'bill': BillDetailSerializer(bill).data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def pending_bills(self, request):
        """Get all pending bills."""
        bills = Bill.objects.filter(status='pending')
        serializer = BillSerializer(bills, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def export_pdf(self, request, pk=None):
        """
        Export bill as PDF.
        GET /api/bills/{id}/export_pdf/
        """
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from django.http import FileResponse

        bill = self.get_object()

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#333333'),
            spaceAfter=10,
        )

        # Title
        story.append(Paragraph("Restaurant Bill", title_style))
        story.append(Spacer(1, 0.3 * inch))

        # Bill info
        info_data = [
            ['Bill Number:', f'#{bill.id}'],
            ['Table Number:', str(bill.table.table_number)],
            ['Date:', bill.created_at.strftime('%Y-%m-%d %H:%M:%S')],
            ['Status:', bill.get_status_display()],
        ]
        info_table = Table(info_data, colWidths=[2 * inch, 2 * inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3 * inch))

        # Items table
        if bill.order:
            items_data = [['Item', 'Qty', 'Price', 'Total']]
            for item in bill.order.items.all():
                items_data.append([
                    item.menu_item.name,
                    str(item.quantity),
                    f'₹{item.menu_item.price}',
                    f'₹{item.get_total_price()}'
                ])

            items_table = Table(items_data, colWidths=[2.5 * inch, 0.8 * inch, 1 * inch, 1 * inch])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(items_table)
            story.append(Spacer(1, 0.2 * inch))

        # Totals
        totals_data = [
            ['Subtotal:', f'₹{bill.subtotal}'],
            ['Tax ({0}%):'.format(bill.tax_percentage), f'₹{bill.tax_amount}'],
            ['Total:', f'₹{bill.total_amount}'],
        ]
        totals_table = Table(totals_data, colWidths=[3 * inch, 1.5 * inch])
        totals_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(totals_table)

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        return FileResponse(
            buffer,
            as_attachment=True,
            filename=f'bill_{bill.id}.pdf',
            content_type='application/pdf'
        )

# ============================================================================
# USER MANAGEMENT VIEWS
# ============================================================================

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for User management.
    Only Manager can view users.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsManager]

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get current user info."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

# ============================================================================
# REPORT VIEWS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_sales_report(request):
    """
    Get daily sales and table usage report.
    GET /api/reports/daily-sales/
    """
    from django.utils import timezone
    from datetime import timedelta

    user = request.user
    if not user.groups.filter(name='Manager').exists():
        return Response(
            {'error': 'Only managers can view reports.'},
            status=status.HTTP_403_FORBIDDEN
        )

    today = timezone.now().date()
    start_of_day = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    end_of_day = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))

    # Get bills for today
    bills = Bill.objects.filter(
        created_at__range=[start_of_day, end_of_day],
        status='paid'
    )

    total_revenue = sum(bill.total_amount for bill in bills)
    total_orders = Order.objects.filter(created_at__range=[start_of_day, end_of_day]).count()
    total_tables_used = len(set(bill.table.id for bill in bills))
    average_bill_value = total_revenue / len(bills) if bills else 0

    return Response({
        'date': today,
        'total_revenue': str(total_revenue),
        'total_bills': len(bills),
        'total_orders': total_orders,
        'total_tables_used': total_tables_used,
        'average_bill_value': str(average_bill_value),
        'bills': BillSerializer(bills, many=True).data
    })

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
from restaurant.models import Table, MenuItem, Order, OrderItem, Bill, Notification

class Command(BaseCommand):
    help = 'Seed database with initial data for testing'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data seed...'))

        # Create user groups/roles
        self.stdout.write(self.style.HTTP_INFO('Creating user roles...'))
        waiter_group, created = Group.objects.get_or_create(name='Waiter')
        cashier_group, created = Group.objects.get_or_create(name='Cashier')
        manager_group, created = Group.objects.get_or_create(name='Manager')

        # Assign permissions to groups
        self._setup_permissions(waiter_group, cashier_group, manager_group)

        # Create test users
        self.stdout.write(self.style.HTTP_INFO('Creating test users...'))
        waiter_user = self._create_user('waiter1', 'waiter@restaurant.com', 'waiter123', waiter_group)
        cashier_user = self._create_user('cashier1', 'cashier@restaurant.com', 'cashier123', cashier_group)
        manager_user = self._create_user('manager1', 'manager@restaurant.com', 'manager123', manager_group)

        self.stdout.write(self.style.SUCCESS(f'✓ Created users: waiter1, cashier1, manager1'))

        # Create tables
        self.stdout.write(self.style.HTTP_INFO('Creating restaurant tables...'))
        tables_data = [
            (1, 2), (2, 2), (3, 4), (4, 4), (5, 6),
            (6, 6), (7, 8), (8, 8), (9, 4), (10, 2)
        ]
        tables = []
        for table_number, capacity in tables_data:
            table, created = Table.objects.get_or_create(
                table_number=table_number,
                defaults={'seating_capacity': capacity, 'status': 'available'}
            )
            tables.append(table)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(tables)} tables'))

        # Create menu items
        self.stdout.write(self.style.HTTP_INFO('Creating menu items...'))
        menu_items_data = [
            # Starters
            ('Samosa', 'starter', 80, 'Crispy fried pastry with spiced filling'),
            ('Paneer Tikka', 'starter', 150, 'Marinated cottage cheese cubes'),
            ('Spring Rolls', 'starter', 120, 'Crispy rolls with vegetable filling'),
            ('Bruschetta', 'starter', 100, 'Toasted bread with tomato and basil'),

            # Main Course
            ('Butter Chicken', 'main', 280, 'Creamy tomato-based chicken curry'),
            ('Paneer Tikka Masala', 'main', 250, 'Cottage cheese in creamy tomato sauce'),
            ('Biryani', 'main', 220, 'Fragrant rice with vegetables'),
            ('Tandoori Chicken', 'main', 300, 'Spiced grilled chicken'),
            ('Dal Makhani', 'main', 180, 'Creamy lentil curry'),
            ('Naan', 'main', 50, 'Traditional Indian bread'),

            # Drinks
            ('Coca Cola', 'drinks', 40, 'Carbonated soft drink'),
            ('Fresh Orange Juice', 'drinks', 60, '100% fresh orange juice'),
            ('Mango Lassi', 'drinks', 80, 'Sweet yogurt drink with mango'),
            ('Iced Tea', 'drinks', 50, 'Refreshing iced tea'),
            ('Water', 'drinks', 20, 'Bottled water'),

            # Desserts
            ('Gulab Jamun', 'dessert', 100, 'Milk solids in sugar syrup'),
            ('Kheer', 'dessert', 90, 'Rice pudding with condensed milk'),
            ('Flan', 'dessert', 110, 'Caramel custard'),
            ('Ice Cream', 'dessert', 80, 'Vanilla ice cream'),
            ('Chocolate Cake', 'dessert', 130, 'Rich chocolate cake'),
        ]

        menu_items = []
        for name, category, price, description in menu_items_data:
            item, created = MenuItem.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'price': price,
                    'description': description,
                    'is_available': True
                }
            )
            menu_items.append(item)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(menu_items)} menu items'))

        # Create sample orders
        self.stdout.write(self.style.HTTP_INFO('Creating sample orders...'))
        table1 = tables[0]
        table1.mark_occupied()
        order1 = Order.objects.create(
            table=table1,
            status='placed',
            notes='No spices on samosa'
        )
        OrderItem.objects.create(
            order=order1,
            menu_item=menu_items[0],  # Samosa
            quantity=2,
            special_notes='Extra crispy'
        )
        OrderItem.objects.create(
            order=order1,
            menu_item=menu_items[11],  # Mango Lassi
            quantity=2
        )

        # Create a bill
        bill1, created = Bill.objects.get_or_create(table=table1)
        bill1.generate_bill(order1)
        self.stdout.write(self.style.SUCCESS('✓ Created sample order and bill'))

        # Create another order (in_kitchen)
        table2 = tables[1]
        table2.mark_occupied()
        order2 = Order.objects.create(
            table=table2,
            status='in_kitchen'
        )
        OrderItem.objects.create(
            order=order2,
            menu_item=menu_items[4],  # Butter Chicken
            quantity=1
        )
        OrderItem.objects.create(
            order=order2,
            menu_item=menu_items[9],  # Naan
            quantity=2
        )
        self.stdout.write(self.style.SUCCESS('✓ Created second order (in_kitchen)'))

        # Create third order (served)
        table3 = tables[2]
        table3.mark_occupied()
        order3 = Order.objects.create(
            table=table3,
            status='served',
            notes='Birthday celebration'
        )
        OrderItem.objects.create(
            order=order3,
            menu_item=menu_items[5],  # Paneer Tikka Masala
            quantity=2
        )
        OrderItem.objects.create(
            order=order3,
            menu_item=menu_items[9],  # Naan
            quantity=3
        )
        OrderItem.objects.create(
            order=order3,
            menu_item=menu_items[17],  # Chocolate Cake
            quantity=1
        )
        self.stdout.write(self.style.SUCCESS('✓ Created third order (served)'))

        # Create fourth order with pending bill
        table4 = tables[3]
        table4.mark_occupied()
        order4 = Order.objects.create(
            table=table4,
            status='served'
        )
        OrderItem.objects.create(
            order=order4,
            menu_item=menu_items[7],  # Tandoori Chicken
            quantity=2
        )
        OrderItem.objects.create(
            order=order4,
            menu_item=menu_items[12],  # Iced Tea
            quantity=2
        )
        bill2, created = Bill.objects.get_or_create(table=table4)
        bill2.generate_bill(order4)
        table4.request_bill()
        self.stdout.write(self.style.SUCCESS('✓ Created fourth order with pending bill'))

        # Create fifth order (completed with paid bill)
        table5 = tables[4]
        order5 = Order.objects.create(
            table=table5,
            status='completed',
            created_at=timezone.now() - timedelta(hours=2)
        )
        OrderItem.objects.create(
            order=order5,
            menu_item=menu_items[1],  # Paneer Tikka
            quantity=1
        )
        OrderItem.objects.create(
            order=order5,
            menu_item=menu_items[6],  # Biryani
            quantity=2
        )
        bill3, created = Bill.objects.get_or_create(table=table5)
        bill3.generate_bill(order5)
        bill3.mark_as_paid()
        self.stdout.write(self.style.SUCCESS('✓ Created fifth order with paid bill'))

        # Create sixth order (completed)
        table6 = tables[5]
        order6 = Order.objects.create(
            table=table6,
            status='completed',
            created_at=timezone.now() - timedelta(hours=4)
        )
        OrderItem.objects.create(
            order=order6,
            menu_item=menu_items[2],  # Spring Rolls
            quantity=2
        )
        OrderItem.objects.create(
            order=order6,
            menu_item=menu_items[8],  # Dal Makhani
            quantity=1
        )
        OrderItem.objects.create(
            order=order6,
            menu_item=menu_items[14],  # Water
            quantity=3
        )
        self.stdout.write(self.style.SUCCESS('✓ Created sixth order (completed)'))

        # Create sample notifications
        self.stdout.write(self.style.HTTP_INFO('Creating sample notifications...'))
        self._create_sample_notifications(manager_user, waiter_user, cashier_user, order1, order2, bill1, bill2)
        self.stdout.write(self.style.SUCCESS('✓ Created sample notifications'))

        self.stdout.write(self.style.SUCCESS('\n=== SEED DATA COMPLETE ==='))
        self.stdout.write(self.style.SUCCESS('\nTest Users Created:'))
        self.stdout.write(f'  Waiter:  username=waiter1, password=waiter123')
        self.stdout.write(f'  Cashier: username=cashier1, password=cashier123')
        self.stdout.write(f'  Manager: username=manager1, password=manager123')
        self.stdout.write(self.style.SUCCESS('\nYou can now test the API with these credentials.'))
        self.stdout.write(self.style.SUCCESS('\nDatabase Summary:'))
        self.stdout.write(f'  ✓ 3 User Accounts (Waiter, Cashier, Manager)')
        self.stdout.write(f'  ✓ 10 Restaurant Tables')
        self.stdout.write(f'  ✓ 20 Menu Items')
        self.stdout.write(f'  ✓ 6 Sample Orders')
        self.stdout.write(f'  ✓ 3 Sample Bills')
        self.stdout.write(f'  ✓ 8 Sample Notifications')
        self.stdout.write(self.style.SUCCESS('\nRun: python manage.py runserver'))
        self.stdout.write(self.style.SUCCESS('Then visit: http://127.0.0.1:8000/api/'))

    def _create_user(self, username, email, password, group):
        """Create a user and add to group."""
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_staff': False,
                'is_active': True,
            }
        )
        if created:
            user.set_password(password)
            user.save()
        user.groups.add(group)
        return user

    def _create_sample_notifications(self, manager_user, waiter_user, cashier_user, order1, order2, bill1, bill2):
        """Create sample notifications for testing."""
        now = timezone.now()

        # Order placed notification
        Notification.objects.get_or_create(
            user=manager_user,
            notification_type='order_placed',
            title='New Order Placed',
            message=f'Table {order1.table.table_number} placed an order for 2x Samosa and 2x Mango Lassi',
            order=order1,
            defaults={'is_read': True, 'created_at': now - timedelta(minutes=10)}
        )

        # Bill pending notification
        Notification.objects.get_or_create(
            user=cashier_user,
            notification_type='bill_pending',
            title='Bill Payment Pending',
            message=f'Table {bill1.table.table_number} has a pending bill of ₹{bill1.total_amount}',
            bill=bill1,
            defaults={'is_read': True, 'created_at': now - timedelta(minutes=5)}
        )

        # Payment received notification
        Notification.objects.get_or_create(
            user=manager_user,
            notification_type='payment_received',
            title='Payment Received',
            message=f'Payment of ₹{bill1.total_amount} received from Table {bill1.table.table_number}',
            bill=bill1,
            defaults={'is_read': True, 'created_at': now - timedelta(minutes=3)}
        )

        # Order ready notification
        Notification.objects.get_or_create(
            user=waiter_user,
            notification_type='order_ready',
            title='Order Ready for Pickup',
            message=f'Order #{order2.id} is ready to serve at Table {order2.table.table_number}',
            order=order2,
            defaults={'is_read': False, 'created_at': now - timedelta(minutes=2)}
        )

        # Bill pending notification (unread)
        Notification.objects.get_or_create(
            user=cashier_user,
            notification_type='bill_pending',
            title='New Bill Pending Payment',
            message=f'Table {bill2.table.table_number} bill is pending - Amount: ₹{bill2.total_amount}',
            bill=bill2,
            defaults={'is_read': False, 'created_at': now - timedelta(minutes=1)}
        )

        # Additional recent notifications
        Notification.objects.get_or_create(
            user=manager_user,
            notification_type='order_placed',
            title='Table 3 Placed New Order',
            message='Paneer Tikka Masala (x2), Naan (x3), Chocolate Cake',
            defaults={'is_read': False, 'created_at': now - timedelta(seconds=30)}
        )

        Notification.objects.get_or_create(
            user=waiter_user,
            notification_type='order_placed',
            title='Kitchen: New Order Received',
            message=f'Order #{order1.id} - Special note: No spices on samosa',
            order=order1,
            defaults={'is_read': False, 'created_at': now - timedelta(seconds=45)}
        )

        Notification.objects.get_or_create(
            user=manager_user,
            notification_type='table_abandoned',
            title='High Table Turnover',
            message='Tables 1-3 completed orders in last 30 minutes',
            defaults={'is_read': False, 'created_at': now}
        )

    def _setup_permissions(self, waiter_group, cashier_group, manager_group):
        """Setup permissions for each group."""
        # Get content types
        ct_table = ContentType.objects.get_for_model(Table)
        ct_menuitem = ContentType.objects.get_for_model(MenuItem)
        ct_order = ContentType.objects.get_for_model(Order)
        ct_orderitem = ContentType.objects.get_for_model(OrderItem)
        ct_bill = ContentType.objects.get_for_model(Bill)
        ct_user = ContentType.objects.get_for_model(User)

        # Waiter permissions
        waiter_perms = Permission.objects.filter(
            content_type__in=[ct_order, ct_orderitem, ct_table, ct_menuitem, ct_bill],
            codename__in=[
                'add_order', 'change_order', 'view_order',
                'add_orderitem', 'change_orderitem', 'view_orderitem',
                'view_table', 'view_menuitem', 'view_bill'
            ]
        )
        waiter_group.permissions.set(waiter_perms)

        # Cashier permissions
        cashier_perms = Permission.objects.filter(
            content_type__in=[ct_bill, ct_order, ct_orderitem, ct_table, ct_menuitem],
            codename__in=[
                'add_bill', 'change_bill', 'view_bill',
                'view_order', 'view_orderitem',
                'view_table', 'view_menuitem'
            ]
        )
        cashier_group.permissions.set(cashier_perms)

        # Manager permissions (all)
        all_perms = Permission.objects.filter(
            content_type__in=[ct_table, ct_menuitem, ct_order, ct_orderitem, ct_bill, ct_user]
        )
        manager_group.permissions.set(all_perms)

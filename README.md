# Restaurant Live Table Order & Billing System

A production-ready Django REST Framework application for managing restaurant dine-in operations with real-time table management, live order tracking, and automated billing system.

## 🎯 Features

### ✅ Core Features Implemented

**1. Table Management**
- Dynamic table status tracking (Available → Occupied → Bill Requested → Closed)
- Real-time dashboard API showing all tables and their current state
- Automatic table status transitions based on order and billing lifecycle
- Seating capacity management

**2. Menu & Orders**
- Categorized menu items (Starters, Main Course, Drinks, Desserts)
- Order creation and item management
- Order status tracking (Placed → In Kitchen → Served)
- Prevention of ordering unavailable items
- Special notes for customization

**3. Billing System**
- Automatic bill generation from orders
- Dynamic tax calculation
- Comprehensive bill details with itemized breakdown
- Bill status management (Not Generated → Pending → Paid)
- Automatic table reset to "Available" after payment
- PDF bill export functionality

**4. Staff Roles & Permissions**
- Role-based access control (RBAC)
- Three roles: Waiter, Cashier, Manager
- Permission enforcement at API level
- Token-based authentication

**5. Notification System**
- Real-time in-app notifications via dropdown popup in navigation bar
- Notification types: Order Placed, Order Ready, Bill Pending, Payment Received, Table Alerts
- Unread notification counter badge
- Recent notifications preview (last 5 notifications)
- Automatic notification cleanup (older than 30 days)

**6. Web Interface**
- Staff dashboard with table management
- Order creation and management interface
- Billing dashboard for cashiers
- Manager reporting and analytics views
- Responsive design using Tailwind CSS

**7. Additional Features**
- Daily sales and table usage reports
- Live dashboard with current table states
- Complete audit trail with timestamps
- Admin dashboard for data management
- Celery background tasks for notifications

## 🏗️ Architecture

### Project Structure
```
Restaurant_Live_Order_Management/
├── restaurant/                    # Main app
│   ├── models.py                 # Database models
│   ├── serializers.py            # DRF serializers
│   ├── views.py                  # ViewSets and views
│   ├── urls.py                   # API endpoints
│   ├── admin.py                  # Django admin config
│   ├── management/
│   │   └── commands/
│   │       └── seed_data.py      # Database seeding
│   ├── migrations/               # Database migrations
│   └── tests.py                  # Unit tests (optional)
├── restaurant_management/         # Project settings
│   ├── settings.py               # Django configuration
│   ├── urls.py                   # Main URL routing
│   ├── wsgi.py                   # WSGI config
│   └── asgi.py                   # ASGI config
├── manage.py                      # Django CLI
├── db.sqlite3                     # SQLite database
└── README.md                      # This file
```

### Technology Stack
- **Framework**: Django 5.2.6
- **API**: Django REST Framework 3.16.1
- **Database**: SQLite3 (easily switchable to PostgreSQL)
- **Authentication**: Token Authentication
- **PDF Export**: ReportLab
- **Task Queue**: Celery (ready for integration)
- **Python**: 3.10+

## 📋 Database Models

### Table
```python
- table_number (Integer, unique)
- seating_capacity (Integer)
- status (Available/Occupied/Bill Requested/Closed)
- created_at, updated_at (Timestamps)
```

### MenuItem
```python
- name (String)
- category (Starter/Main/Drinks/Dessert)
- price (Decimal)
- description (Text)
- is_available (Boolean)
- created_at, updated_at (Timestamps)
```

### Order
```python
- table (ForeignKey to Table)
- status (Placed/In Kitchen/Served/Cancelled)
- notes (Text)
- created_at, updated_at (Timestamps)
```

### OrderItem
```python
- order (ForeignKey to Order)
- menu_item (ForeignKey to MenuItem)
- quantity (Integer)
- special_notes (Text)
- created_at (Timestamp)
```

### Bill
```python
- table (OneToOneField to Table)
- order (OneToOneField to Order)
- subtotal (Decimal)
- tax_percentage (Decimal, default 5%)
- tax_amount (Decimal)
- total_amount (Decimal)
- status (Not Generated/Pending/Paid/Cancelled)
- created_at, updated_at, paid_at (Timestamps)
```

### Notification
```python
- user (ForeignKey to User)
- notification_type (Order Placed/Order Ready/Bill Pending/Payment Received/Table Alert)
- title (String)
- message (Text)
- order (ForeignKey to Order, nullable)
- bill (ForeignKey to Bill, nullable)
- table (ForeignKey to Table, nullable)
- is_read (Boolean)
- created_at (Timestamp)
- read_at (Timestamp, nullable)
```

## 🚀 Setup Instructions

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)
- Git

### Installation

1. **Clone the Repository**
```bash
cd Restaurant_Live_Table_Order_Billing_System
```

2. **Create Virtual Environment** (Optional but recommended)
```bash
python -m venv venv
source venv/Scripts/activate  # On Windows
# or
source venv/bin/activate  # On Linux/Mac
```

3. **Install Dependencies**
```bash
pip install django==5.2.6 djangorestframework==3.16.1 python-decouple pillow celery redis psycopg2-binary reportlab
```

4. **Run Migrations**
```bash
python manage.py migrate
```

5. **Seed Database with Sample Data**
```bash
python manage.py seed_data
```

6. **Create Superuser (Optional, for Django Admin)**
```bash
python manage.py createsuperuser
```

7. **Run Development Server**
```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/api/`

## 🔐 Authentication & Credentials

### Default Test Users

| Role | Username | Password | Email |
|------|----------|----------|-------|
| Waiter | `waiter1` | `waiter123` | waiter@restaurant.com |
| Cashier | `cashier1` | `cashier123` | cashier@restaurant.com |
| Manager | `manager1` | `manager123` | manager@restaurant.com |

### Login Flow

1. **Get Token**
```bash
POST /api/auth/login/
{
    "username": "waiter1",
    "password": "waiter123"
}
```

**Response:**
```json
{
    "token": "abc123xyz789",
    "user": {
        "id": 1,
        "username": "waiter1",
        "email": "waiter@restaurant.com",
        "groups": ["Waiter"],
        "is_active": true
    }
}
```

2. **Use Token in Requests**
```bash
Authorization: Token abc123xyz789
```

3. **Logout**
```bash
POST /api/auth/logout/
Header: Authorization: Token abc123xyz789
```

## 📡 API Endpoints

### Tables
```
GET    /api/tables/                    # List all tables
POST   /api/tables/                    # Create table (Manager only)
GET    /api/tables/{id}/               # Get table details
PUT    /api/tables/{id}/               # Update table (Manager only)
DELETE /api/tables/{id}/               # Delete table (Manager only)
GET    /api/tables/dashboard/          # Live dashboard (all authenticated users)
POST   /api/tables/{id}/request_bill/  # Request bill (Waiter)
```

### Menu Items
```
GET    /api/menu-items/                # List menu items
POST   /api/menu-items/                # Create item (Manager only)
GET    /api/menu-items/{id}/           # Get item details
PUT    /api/menu-items/{id}/           # Update item (Manager only)
DELETE /api/menu-items/{id}/           # Delete item (Manager only)
```

### Orders
```
GET    /api/orders/                    # List orders
POST   /api/orders/                    # Create order (Waiter)
GET    /api/orders/{id}/               # Get order details
POST   /api/orders/{id}/add_item/      # Add item to order (Waiter)
DELETE /api/orders/{id}/remove_item/   # Remove item from order
POST   /api/orders/{id}/send_to_kitchen/  # Send to kitchen
POST   /api/orders/{id}/mark_served/   # Mark as served
```

### Bills
```
GET    /api/bills/                     # List bills
GET    /api/bills/pending_bills/       # Get pending bills (Cashier)
POST   /api/bills/{id}/generate_bill/  # Generate bill (Cashier)
POST   /api/bills/{id}/mark_as_paid/   # Mark as paid (Cashier)
GET    /api/bills/{id}/export_pdf/     # Export bill as PDF
```

### Reports
```
GET    /api/reports/daily-sales/       # Daily sales report (Manager only)
```

### Users
```
GET    /api/users/me/                  # Get current user info
```

## 📝 Example API Workflows

### Workflow 1: Create Order and Generate Bill

**Step 1: Login as Waiter**
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "waiter1", "password": "waiter123"}'
```

**Step 2: Create Order for Table 1**
```bash
curl -X POST http://127.0.0.1:8000/api/orders/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"table": 1, "notes": "No onions"}'
```

**Step 3: Add Menu Items to Order**
```bash
curl -X POST http://127.0.0.1:8000/api/orders/1/add_item/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"menu_item": 5, "quantity": 2, "special_notes": "Extra crispy"}'
```

**Step 4: Send Order to Kitchen**
```bash
curl -X POST http://127.0.0.1:8000/api/orders/1/send_to_kitchen/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Step 5: Mark Order as Served**
```bash
curl -X POST http://127.0.0.1:8000/api/orders/1/mark_served/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Step 6: Login as Cashier and Generate Bill**
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "cashier1", "password": "cashier123"}'
```

**Step 7: Generate Bill**
```bash
curl -X POST http://127.0.0.1:8000/api/bills/1/generate_bill/ \
  -H "Authorization: Token CASHIER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"order": 1}'
```

**Step 8: Mark Bill as Paid**
```bash
curl -X POST http://127.0.0.1:8000/api/bills/1/mark_as_paid/ \
  -H "Authorization: Token CASHIER_TOKEN"
```

**Step 9: Export Bill as PDF**
```bash
curl -X GET http://127.0.0.1:8000/api/bills/1/export_pdf/ \
  -H "Authorization: Token CASHIER_TOKEN" \
  -o bill_1.pdf
```

**Table Status Changes:**
- ✅ Step 1: Table 1 becomes "Occupied"
- ✅ Step 8: Table 1 becomes "Bill Requested"
- ✅ Step 8: Table 1 resets to "Available"

## 🔑 Role-Based Permissions

### Waiter
- ✅ Create orders
- ✅ Add/remove items from orders
- ✅ Send orders to kitchen
- ✅ Mark orders as served
- ✅ Request bills
- ✅ View tables, menu items, and orders
- ❌ Cannot create/modify tables or menus
- ❌ Cannot generate or modify bills

### Cashier
- ✅ Generate bills
- ✅ Mark bills as paid
- ✅ View pending bills
- ✅ Export bills as PDF
- ✅ View orders, tables, and menu items
- ❌ Cannot create orders
- ❌ Cannot create/modify tables or menus

### Manager
- ✅ Full access to all features
- ✅ Create/edit/delete tables
- ✅ Create/edit/delete menu items
- ✅ View all reports
- ✅ Manage users and permissions
- ✅ Access Django admin

## 📊 Database Schema

### ER Diagram
![ER Diagram](ER%20Diagram.png)

### Relationships
```
Table (1) ──────────── (many) Order
  │
  └─────────────── (1) Bill ──────────── (1) Order
  
Order (1) ──────────── (many) OrderItem
  │
  └────────────────── (many) MenuItem

User (1) ──────────── (many) Notification
  │
  └── Links to Order, Bill, or Table
```

## 💾 Sample Seed Data

The project includes a comprehensive seed data command that creates:

**3 Test Users:**
- Waiter (username: waiter1, password: waiter123)
- Cashier (username: cashier1, password: cashier123)
- Manager (username: manager1, password: manager123)

**10 Restaurant Tables** with varying seating capacity (2-8 seats)

**20 Menu Items** across 4 categories:
- **Starters**: Samosa, Paneer Tikka, Spring Rolls, Bruschetta
- **Main Courses**: Butter Chicken, Paneer Tikka Masala, Biryani, Tandoori Chicken, Dal Makhani, Naan
- **Drinks**: Coca Cola, Fresh Orange Juice, Mango Lassi, Iced Tea, Water
- **Desserts**: Gulab Jamun, Kheer, Flan, Ice Cream, Chocolate Cake

**6 Sample Orders** in different states:
- Order 1: Placed status with generated bill
- Order 2: In kitchen status
- Order 3: Served status (Birthday celebration)
- Order 4: Served with pending bill
- Order 5: Completed with paid bill
- Order 6: Completed from 4 hours ago

**3 Sample Bills:**
- Bill 1: Generated from Order 1
- Bill 2: Pending payment
- Bill 3: Paid status

**8 Sample Notifications:**
- Order placed notifications
- Bill pending notifications (both read and unread)
- Payment received notification
- Order ready notification
- Table turnover alert
- Various timestamps showing recent activity

**Run the seed command:**
```bash
python manage.py seed_data
```

This creates a realistic test environment with multiple order states and notification types for comprehensive testing.

## 🎨 Admin Dashboard

Access the Django admin at `http://127.0.0.1:8000/admin/`

**Default Admin Credentials:**
- Create with: `python manage.py createsuperuser`
- Username: (your choice)
- Password: (your choice)

## 🧪 Testing the API

### Using cURL
```bash
# List all tables
curl -H "Authorization: Token YOUR_TOKEN" \
  http://127.0.0.1:8000/api/tables/

# View dashboard
curl -H "Authorization: Token YOUR_TOKEN" \
  http://127.0.0.1:8000/api/tables/dashboard/

# Daily sales report (Manager only)
curl -H "Authorization: Token MANAGER_TOKEN" \
  http://127.0.0.1:8000/api/reports/daily-sales/
```

### Using Python Requests
```python
import requests

BASE_URL = "http://127.0.0.1:8000/api"

# Login
response = requests.post(f"{BASE_URL}/auth/login/", json={
    "username": "waiter1",
    "password": "waiter123"
})
token = response.json()['token']

# List tables
headers = {"Authorization": f"Token {token}"}
tables = requests.get(f"{BASE_URL}/tables/", headers=headers)
print(tables.json())
```

## 🔧 Configuration

### Database
Currently using SQLite. To switch to PostgreSQL:

1. Install PostgreSQL adapter:
```bash
pip install psycopg2-binary
```

2. Update `restaurant_management/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'restaurant_db',
        'USER': 'postgres',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Tax Configuration
Default tax is 5%. To change, update in `restaurant/models.py` or through admin.

## 📦 Production Deployment

### Environment Variables (create `.env` file)
```
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@host:port/dbname
```

### Use production-grade server
```bash
pip install gunicorn
gunicorn restaurant_management.wsgi:application --bind 0.0.0.0:8000
```

## 🐳 Docker Setup

Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "restaurant_management.wsgi:application", "--bind", "0.0.0.0:8000"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/restaurant
    depends_on:
      - db
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=restaurant
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Run with Docker:
```bash
docker-compose up
```

## 📋 Assumptions & Design Decisions

1. **Single Bill per Table**: One active bill per table at a time
2. **Tax Calculation**: Fixed percentage tax applied on subtotal
3. **Status Flow**: Tables follow a strict lifecycle (Available → Occupied → Bill Requested → Available)
4. **Token Authentication**: Stateless, scalable authentication method
5. **SQLite for Development**: Easy to setup; switch to PostgreSQL for production
6. **Timestamps in IST**: Asia/Kolkata timezone configured
7. **Decimal Prices**: Financial accuracy using Django's DecimalField
8. **Soft Delete Not Used**: Hard delete for simplicity; can be added later

## 🔮 Future Enhancements

- [ ] WebSocket real-time updates using Django Channels
- [ ] Kitchen display system (KDS) integration
- [ ] Customer feedback and ratings
- [ ] Inventory management
- [ ] Advanced analytics and reporting
- [ ] Multi-restaurant support
- [ ] Mobile app (React Native/Flutter)
- [ ] Payment gateway integration (Stripe, Razorpay)
- [ ] Table reservations
- [ ] QR code for table ordering

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'rest_framework'"
```bash
pip install djangorestframework
```

### "No such table: restaurant_table"
```bash
python manage.py makemigrations
python manage.py migrate
```

### "Authorization credentials were not provided"
- Ensure you're sending `Authorization: Token YOUR_TOKEN` header
- Get token via `/api/auth/login/`

### CORS Issues (if frontend is separate)
```bash
pip install django-cors-headers
# Add to INSTALLED_APPS and MIDDLEWARE in settings.py
```

## 📞 Support

For issues and questions, refer to:
- Django Documentation: https://docs.djangoproject.com/
- Django REST Framework: https://www.django-rest-framework.org/
- Code comments in the project

## 📄 License

This project is provided as-is for educational and commercial use.

---

**Built with ❤️ using Django & Django REST Framework**

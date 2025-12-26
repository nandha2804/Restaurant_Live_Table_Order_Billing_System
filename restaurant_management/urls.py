from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from restaurant import views_web


from rest_framework.routers import DefaultRouter
from restaurant import views

router = DefaultRouter()
router.register(r'tables', views.TableViewSet, basename='table')
router.register(r'menu-items', views.MenuItemViewSet, basename='menuitem')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'bills', views.BillViewSet, basename='bill')
router.register(r'users', views.UserViewSet, basename='user')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Web Routes (Templates)
    path('', views_web.home, name='home'),
    path('login/', views_web.login_view, name='login'),
    path('logout/', views_web.logout_view, name='logout'),
    path('dashboard/', views_web.dashboard, name='dashboard'),
    
    # Orders (Waiter)
    path('orders/', views_web.orders_list, name='orders'),
    path('orders/create/', views_web.create_order, name='create-order'),
    path('orders/<int:order_id>/', views_web.order_detail, name='order-detail'),
    path('orders/<int:order_id>/send-to-kitchen/', views_web.send_to_kitchen, name='send-to-kitchen'),
    path('orders/<int:order_id>/mark-served/', views_web.mark_served, name='mark-served'),
    
    # Billing (Cashier)
    path('billing/', views_web.billing_dashboard, name='billing'),
    path('billing/<int:table_id>/generate/', views_web.generate_bill, name='generate-bill'),
    path('bills/<int:bill_id>/', views_web.bill_detail, name='bill-detail'),
    path('bills/<int:bill_id>/mark-paid/', views_web.mark_paid, name='mark-paid'),
    
    # Manager
    path('menu/', views_web.menu_list, name='menu-list'),
    path('tables/', views_web.table_list, name='table-list'),
    path('reports/', views_web.reports, name='reports'),
    
    path('auth/login/', views.obtain_token, name='auth_login'),
    path('auth/logout/', views.logout, name='auth_logout'),
    
    # Reports
    path('reports/daily-sales/', views.daily_sales_report, name='daily_sales_report'),
    
    
]

from django.urls import path
from . import views_web

urlpatterns = [
    # Authentication
    path('login/', views_web.login_view, name='login'),
    path('logout/', views_web.logout_view, name='logout'),
    
    # Dashboard
    path('', views_web.dashboard, name='dashboard'),
    
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
]

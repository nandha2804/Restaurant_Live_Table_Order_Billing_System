from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tables', views.TableViewSet, basename='table')
router.register(r'menu-items', views.MenuItemViewSet, basename='menuitem')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'bills', views.BillViewSet, basename='bill')
router.register(r'users', views.UserViewSet, basename='user')

urlpatterns = [
    # Auth endpoints
    path('auth/login/', views.obtain_token, name='auth_login'),
    path('auth/logout/', views.logout, name='auth_logout'),
    
    # Reports
    path('reports/daily-sales/', views.daily_sales_report, name='daily_sales_report'),
    
    # Router endpoints
    path('', include(router.urls)),
]

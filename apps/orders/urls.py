from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'order-items', views.OrderItemViewSet, basename='order-item')
router.register(r'payments', views.PaymentViewSet, basename='payment')

urlpatterns = [
    # Основные маршруты
    path('', include(router.urls)),
    
    # Мои заказы
    path('my-orders/', views.MyOrdersView.as_view(), name='my-orders'),
    
    # Статистика
    path('stats/', views.OrderStatsView.as_view(), name='order-stats'),
    
    # Специфичные маршруты заказов
    path('orders/<int:pk>/approve/', 
         views.OrderViewSet.as_view({'post': 'approve'}), 
         name='order-approve'),
    
    path('orders/<int:pk>/cancel/', 
         views.OrderViewSet.as_view({'post': 'cancel'}), 
         name='order-cancel'),
    
    path('orders/<int:pk>/status/', 
         views.OrderViewSet.as_view({'patch': 'status'}), 
         name='order-status'),
    
    path('orders/<int:pk>/history/', 
         views.OrderViewSet.as_view({'get': 'history'}), 
         name='order-history'),
    
    path('orders/<int:pk>/items/', 
         views.OrderViewSet.as_view({'get': 'items'}), 
         name='order-items'),
    
    path('orders/<int:pk>/stats/', 
         views.OrderViewSet.as_view({'get': 'stats'}), 
         name='order-stats-detail'),
    
    # Создание из корзины
    path('orders/from-cart/', 
         views.OrderViewSet.as_view({'post': 'from_cart'}), 
         name='order-from-cart'),
]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Создаем роутер для автоматической генерации URL
router = DefaultRouter()

# Ручная регистрация URL (более понятно)
urlpatterns = [
    # Корзина
    path('', views.CartViewSet.as_view({'get': 'list'}), name='cart-detail'),
    path('clear/', views.CartViewSet.as_view({'post': 'clear'}), name='cart-clear'),
    path('set-store/', views.CartViewSet.as_view({'post': 'set_store'}), name='cart-set-store'),
    
    # Товары в корзине
    path('items/', views.CartItemViewSet.as_view({'post': 'create'}), name='cart-item-create'),
    path('items/<int:pk>/', views.CartItemViewSet.as_view({
        'put': 'update',
        'delete': 'destroy'
    }), name='cart-item-detail'),
    path('items/batch-update/', views.CartItemViewSet.as_view({
        'post': 'batch_update'
    }), name='cart-item-batch-update'),
    
]

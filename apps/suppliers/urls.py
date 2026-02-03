from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.SupplierViewSet, basename='supplier')

urlpatterns = [
    # Административные маршруты (только для админов)
    path('', include(router.urls)),
    
    # Публичные маршруты (для всех авторизованных)
    path('public/', views.SupplierPublicView.as_view(), name='suppliers-public'),
    
    # Маршруты для текущего поставщика
    path('me/', views.MySupplierProfileView.as_view(), name='supplier-me'),
    path('me/dashboard/', views.SupplierDashboardView.as_view(), name='supplier-dashboard'),
    
    # Заказы поставщика
    path('me/orders/', views.SupplierOrdersView.as_view(), name='supplier-orders'),
    path('me/orders/summary/', 
         views.SupplierOrdersView.as_view({'get': 'summary'}), 
         name='supplier-orders-summary'),
    
    # Товары поставщика
    path('me/products/', views.SupplierProductsView.as_view(), name='supplier-products'),
    
    # Дополнительные административные маршруты
    path('<int:pk>/performance/', 
         views.SupplierViewSet.as_view({'get': 'performance'}), 
         name='supplier-performance'),
    
    path('<int:pk>/products/', 
         views.SupplierViewSet.as_view({'get': 'products'}), 
         name='supplier-products-list'),
    
    path('<int:pk>/orders/', 
         views.SupplierViewSet.as_view({'get': 'orders'}), 
         name='supplier-orders-list'),
    
    path('<int:pk>/activate/', 
         views.SupplierViewSet.as_view({'post': 'activate'}), 
         name='supplier-activate'),
    
    path('<int:pk>/deactivate/', 
         views.SupplierViewSet.as_view({'post': 'deactivate'}), 
         name='supplier-deactivate'),
    
    path('<int:pk>/generate-report/', 
         views.SupplierViewSet.as_view({'post': 'generate_report'}), 
         name='supplier-generate-report'),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.AnalyticsViewSet, basename='analytics')

urlpatterns = [
    # Все маршруты через router
    path('', include(router.urls)),
    
    # Дополнительные маршруты
    path('realtime/', views.RealTimeAnalyticsView.as_view(), name='analytics-realtime'),
    
    # Альтернативный подход с явным указанием путей
    path('orders-stats/', 
         views.AnalyticsViewSet.as_view({'get': 'orders_stats'}), 
         name='orders-stats'),
    
    path('budget/', 
         views.AnalyticsViewSet.as_view({'get': 'budget'}), 
         name='budget-report'),
    
    path('top-products/', 
         views.AnalyticsViewSet.as_view({'get': 'top_products'}), 
         name='top-products'),
    
    path('sales-trend/', 
         views.AnalyticsViewSet.as_view({'get': 'sales_trend'}), 
         name='sales-trend'),
    
    path('supplier-performance/', 
         views.AnalyticsViewSet.as_view({'get': 'supplier_performance'}), 
         name='supplier-performance'),
    
    path('daily-report/', 
         views.AnalyticsViewSet.as_view({'get': 'daily_report'}), 
         name='daily-report'),
    
    path('export-excel/', 
         views.AnalyticsViewSet.as_view({'get': 'export_excel'}), 
         name='export-excel'),
    
    path('custom-report/', 
         views.AnalyticsViewSet.as_view({'post': 'custom_report'}), 
         name='custom-report'),
]

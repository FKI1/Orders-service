from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'networks', views.RetailNetworkViewSet, basename='network')
router.register(r'stores', views.StoreViewSet, basename='store')

urlpatterns = [
    # Основные маршруты
    path('', include(router.urls)),
    
    # Мои сети и магазины
    path('my-networks/', views.MyNetworksView.as_view(), name='my-networks'),
    path('my-stores/', views.MyStoresView.as_view(), name='my-stores'),
    
    # Специфичные маршруты сетей
    path('networks/<int:pk>/stats/', 
         views.RetailNetworkViewSet.as_view({'get': 'stats'}), 
         name='network-stats'),
    
    path('networks/<int:pk>/dashboard/', 
         views.RetailNetworkViewSet.as_view({'get': 'dashboard'}), 
         name='network-dashboard'),
    
    path('networks/<int:pk>/stores/', 
         views.RetailNetworkViewSet.as_view({'get': 'stores'}), 
         name='network-stores'),
    
    path('networks/<int:pk>/employees/', 
         views.RetailNetworkViewSet.as_view({'get': 'employees'}), 
         name='network-employees'),
    
    path('networks/<int:pk>/add-administrator/', 
         views.RetailNetworkViewSet.as_view({'post': 'add_administrator'}), 
         name='network-add-admin'),
    
    path('networks/<int:pk>/remove-administrator/', 
         views.RetailNetworkViewSet.as_view({'post': 'remove_administrator'}), 
         name='network-remove-admin'),
    
    path('networks/<int:pk>/update-budget/', 
         views.RetailNetworkViewSet.as_view({'patch': 'update_budget'}), 
         name='network-update-budget'),
    
    path('networks/<int:pk>/settings/', 
         views.RetailNetworkViewSet.as_view({'get': 'settings'}), 
         name='network-settings'),
    
    path('networks/<int:pk>/update-settings/', 
         views.RetailNetworkViewSet.as_view({'put': 'update_settings'}), 
         name='network-update-settings'),
    
    # Специфичные маршруты магазинов
    path('stores/<int:pk>/stats/', 
         views.StoreViewSet.as_view({'get': 'stats'}), 
         name='store-stats'),
    
    path('stores/<int:pk>/dashboard/', 
         views.StoreViewSet.as_view({'get': 'dashboard'}), 
         name='store-dashboard'),
    
    path('stores/<int:pk>/orders/', 
         views.StoreViewSet.as_view({'get': 'orders'}), 
         name='store-orders'),
    
    path('stores/<int:pk>/employees/', 
         views.StoreViewSet.as_view({'get': 'employees'}), 
         name='store-employees'),
    
    path('stores/<int:pk>/assign-employee/', 
         views.StoreViewSet.as_view({'post': 'assign_employee'}), 
         name='store-assign-employee'),
    
    path('stores/<int:pk>/remove-employee/', 
         views.StoreViewSet.as_view({'post': 'remove_employee'}), 
         name='store-remove-employee'),
    
    path('stores/<int:pk>/update-budget/', 
         views.StoreViewSet.as_view({'patch': 'update_budget'}), 
         name='store-update-budget'),
    
    path('stores/<int:pk>/change-status/', 
         views.StoreViewSet.as_view({'post': 'change_status'}), 
         name='store-change-status'),
]

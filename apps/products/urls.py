from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'product-images', views.ProductImageViewSet, basename='product-image')
router.register(r'reviews', views.ProductReviewViewSet, basename='review')

urlpatterns = [
    # Основные маршруты
    path('', include(router.urls)),
    
    # Поиск
    path('search/', views.SearchProductsView.as_view(), name='product-search'),
    
    # Популярные товары
    path('popular/', views.PopularProductsView.as_view(), name='popular-products'),
    
    # Рекомендованные товары
    path('recommended/', views.RecommendedProductsView.as_view(), name='recommended-products'),
    
    # Мои товары (для поставщиков)
    path('my-products/', views.MyProductsView.as_view(), name='my-products'),
    
    # Экспорт
    path('export/', views.ExportProductsView.as_view(), name='export-products'),
    
    # Специфичные маршруты товаров
    path('products/<int:pk>/update-stock/', 
         views.ProductViewSet.as_view({'post': 'update_stock'}), 
         name='product-update-stock'),
    
    path('products/<int:pk>/reserve/', 
         views.ProductViewSet.as_view({'post': 'reserve'}), 
         name='product-reserve'),
    
    path('products/<int:pk>/release/', 
         views.ProductViewSet.as_view({'post': 'release'}), 
         name='product-release'),
    
    path('products/<int:pk>/stats/', 
         views.ProductViewSet.as_view({'get': 'stats'}), 
         name='product-stats'),
    
    path('products/<int:pk>/related/', 
         views.ProductViewSet.as_view({'get': 'related'}), 
         name='product-related'),
    
    path('products/<int:pk>/reviews/', 
         views.ProductViewSet.as_view({'get': 'reviews'}), 
         name='product-reviews'),
    
    # Специфичные маршруты категорий
    path('categories/<int:pk>/products/', 
         views.CategoryViewSet.as_view({'get': 'products'}), 
         name='category-products'),
    
    path('categories/<int:pk>/stats/', 
         views.CategoryViewSet.as_view({'get': 'stats'}), 
         name='category-stats'),
    
    # Специфичные маршруты отзывов
    path('reviews/<int:pk>/approve/', 
         views.ProductReviewViewSet.as_view({'post': 'approve'}), 
         name='review-approve'),
]
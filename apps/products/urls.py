from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Основной роутер
router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'product-images', views.ProductImageViewSet, basename='product-image')
router.register(r'reviews', views.ProductReviewViewSet, basename='review')

router.register(r'specifications', views.ProductSpecificationViewSet, basename='specification')

urlpatterns = [
    
    path('', include(router.urls)),

    path('search/', views.SearchProductsView.as_view(), name='product-search'),
    path('popular/', views.PopularProductsView.as_view(), name='popular-products'),
    path('recommended/', views.RecommendedProductsView.as_view(), name='recommended-products'),
    path('new-arrivals/', views.ProductViewSet.as_view({'get': 'new_arrivals'}), name='new-arrivals'),
    path('bestsellers/', views.ProductViewSet.as_view({'get': 'bestsellers'}), name='bestsellers'),
    
    path('my-products/', views.MyProductsView.as_view(), name='my-products'),
    path('export/', views.ExportProductsView.as_view(), name='export-products'),
    
    # Получение спецификации по slug товара
    path('products/<slug:slug>/specification/', 
         views.ProductSpecificationByProductView.as_view(), 
         name='product-specification-by-slug'),
    
    # Обновление спецификации по slug товара
    path('products/<slug:slug>/specification/update/', 
         views.ProductSpecificationUpdateByProductView.as_view(), 
         name='product-specification-update-by-slug'),
    
    # Получение спецификации по ID товара (через action в ProductViewSet)
    path('products/<int:pk>/specification/', 
         views.ProductViewSet.as_view({'get': 'specification'}), 
         name='product-specification'),
    
    # Создание/обновление спецификации по ID товара
    path('products/<int:pk>/update-specification/', 
         views.ProductViewSet.as_view({'post': 'update_specification', 
                                      'put': 'update_specification', 
                                      'patch': 'update_specification'}), 
         name='product-update-specification'),
    
    # Кастомные маршруты для спецификаций (через SpecificationViewSet)
    path('specifications/by-product/', 
         views.ProductSpecificationViewSet.as_view({'get': 'by_product'}), 
         name='specification-by-product'),
    
    path('specifications/by-supplier/', 
         views.ProductSpecificationViewSet.as_view({'get': 'by_supplier'}), 
         name='specification-by-supplier'),
    
    path('specifications/<int:pk>/export/', 
         views.ProductSpecificationViewSet.as_view({'get': 'export'}), 
         name='specification-export'),
    
    # Управление складом
    path('products/<int:pk>/update-stock/', 
         views.ProductViewSet.as_view({'post': 'update_stock'}), 
         name='product-update-stock'),
    
    path('products/<int:pk>/reserve/', 
         views.ProductViewSet.as_view({'post': 'reserve'}), 
         name='product-reserve'),
    
    path('products/<int:pk>/release/', 
         views.ProductViewSet.as_view({'post': 'release'}), 
         name='product-release'),
    
    # Статистика и связанные товары
    path('products/<int:pk>/stats/', 
         views.ProductViewSet.as_view({'get': 'stats'}), 
         name='product-stats'),
    
    path('products/<int:pk>/related/', 
         views.ProductViewSet.as_view({'get': 'related'}), 
         name='product-related'),
    
    path('products/<int:pk>/reviews/', 
         views.ProductViewSet.as_view({'get': 'reviews'}), 
         name='product-reviews'),
    
    path('categories/<int:pk>/products/', 
         views.CategoryViewSet.as_view({'get': 'products'}), 
         name='category-products'),
    
    path('categories/<int:pk>/stats/', 
         views.CategoryViewSet.as_view({'get': 'stats'}), 
         name='category-stats'),
    
    path('product-images/<int:pk>/set-main/', 
         views.ProductImageViewSet.as_view({'post': 'set_main'}), 
         name='product-image-set-main'),

    path('reviews/<int:pk>/approve/', 
         views.ProductReviewViewSet.as_view({'post': 'approve'}), 
         name='review-approve'),
    
    path('reviews/<int:pk>/helpful/', 
         views.ProductReviewViewSet.as_view({'post': 'helpful'}), 
         name='review-helpful'),
    
    path('reviews/<int:pk>/not-helpful/', 
         views.ProductReviewViewSet.as_view({'post': 'not_helpful'}), 
         name='review-not-helpful'),
]

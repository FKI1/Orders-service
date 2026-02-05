from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, Avg, F
from django.utils import timezone
from datetime import timedelta

from .models import Product, Category, ProductImage, ProductReview
from .serializers import (
    ProductSerializer,
    ProductDetailSerializer,
    CategorySerializer,
    ProductImageSerializer,
    ProductReviewSerializer,
    CreateProductSerializer,
    UpdateProductSerializer,
    ProductStatsSerializer
)
from .permissions import (
    CanViewProduct,
    CanCreateProduct,
    CanUpdateProduct,
    CanDeleteProduct,
    IsSupplierOrAdmin
)
from .filters import ProductFilter, CategoryFilter
from .services import (
    search_products,
    get_products_by_category,
    get_popular_products,
    get_recommended_products,
    update_product_stock,
    calculate_product_statistics,
    export_products_to_csv
)


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления товарами.
    """
    queryset = Product.objects.all().select_related(
        'category', 'supplier'
    ).prefetch_related('images')
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'sku', 'short_description', 'description']
    ordering_fields = [
        'name', 'price', 'created_at', 'updated_at', 
        'rating', 'total_ordered'
    ]
    
    def get_permissions(self):
        """
        Динамические разрешения в зависимости от действия.
        """
        if self.action == 'list':
            self.permission_classes = [IsAuthenticated, CanViewProduct]
        elif self.action == 'retrieve':
            self.permission_classes = [IsAuthenticated, CanViewProduct]
        elif self.action == 'create':
            self.permission_classes = [IsAuthenticated, CanCreateProduct]
        elif self.action in ['update', 'partial_update']:
            self.permission_classes = [IsAuthenticated, CanUpdateProduct]
        elif self.action == 'destroy':
            self.permission_classes = [IsAuthenticated, CanDeleteProduct]
        else:
            self.permission_classes = [IsAuthenticated]
        
        return super().get_permissions()
    
    def get_queryset(self):
        """
        Фильтрация товаров в зависимости от прав пользователя.
        """
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            return self.queryset.all()
        
        # Поставщик видит только свои товары
        if user.role == 'supplier':
            return self.queryset.filter(supplier=user)
        
        # Остальные пользователи видят только активные товары
        return self.queryset.filter(
            status=Product.ProductStatus.ACTIVE,
            in_stock=True
        )
    
    def get_serializer_class(self):
        """
        Выбор сериализатора в зависимости от действия.
        """
        if self.action == 'create':
            return CreateProductSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateProductSerializer
        elif self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductSerializer
    
    def perform_create(self, serializer):
        """
        Создание товара.
        """
        # Для поставщиков автоматически устанавливаем их как владельца
        if self.request.user.role == 'supplier':
            serializer.save(supplier=self.request.user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def update_stock(self, request, pk=None):
        """
        POST /api/products/{id}/update-stock/
        Обновить количество на складе.
        """
        product = self.get_object()
        quantity = request.data.get('quantity')
        
        if quantity is None:
            return Response(
                {'error': 'Не указано количество'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quantity = int(quantity)
            if quantity < 0:
                return Response(
                    {'error': 'Количество не может быть отрицательным'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            update_product_stock(product, quantity)
            
            return Response({
                'success': 'Количество обновлено',
                'stock_quantity': product.stock_quantity,
                'available_quantity': product.available_quantity
            })
        
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reserve(self, request, pk=None):
        """
        POST /api/products/{id}/reserve/
        Зарезервировать товар.
        """
        product = self.get_object()
        quantity = request.data.get('quantity')
        
        if quantity is None:
            return Response(
                {'error': 'Не указано количество'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quantity = int(quantity)
            product.reserve_quantity(quantity)
            
            return Response({
                'success': f'Зарезервировано {quantity} единиц',
                'reserved_quantity': product.reserved_quantity,
                'available_quantity': product.available_quantity
            })
        
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """
        POST /api/products/{id}/release/
        Освободить зарезервированный товар.
        """
        product = self.get_object()
        quantity = request.data.get('quantity')
        
        if quantity is None:
            return Response(
                {'error': 'Не указано количество'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quantity = int(quantity)
            product.release_quantity(quantity)
            
            return Response({
                'success': f'Освобождено {quantity} единиц',
                'reserved_quantity': product.reserved_quantity,
                'available_quantity': product.available_quantity
            })
        
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        GET /api/products/{id}/stats/
        Статистика товара.
        """
        product = self.get_object()
        stats = calculate_product_statistics(product)
        serializer = ProductStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def related(self, request, pk=None):
        """
        GET /api/products/{id}/related/
        Похожие товары.
        """
        product = self.get_object()
        related_products = product.get_related_products(limit=4)
        serializer = ProductSerializer(related_products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """
        GET /api/products/{id}/reviews/
        Отзывы о товаре.
        """
        product = self.get_object()
        reviews = product.reviews.filter(is_approved=True).order_by('-created_at')
        
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ProductReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductReviewSerializer(reviews, many=True)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для категорий товаров.
    """
    queryset = Category.objects.filter(is_active=True).prefetch_related('children')
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = CategoryFilter
    search_fields = ['name', 'description']
    
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """
        GET /api/categories/{id}/products/
        Товары категории.
        """
        category = self.get_object()
        products = get_products_by_category(category, request.user)
        
        # Применяем фильтры из запроса
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        in_stock = request.query_params.get('in_stock')
        
        if min_price:
            products = products.filter(price__gte=min_price)
        if max_price:
            products = products.filter(price__lte=max_price)
        if in_stock and in_stock.lower() == 'true':
            products = products.filter(in_stock=True)
        
        # Пагинация
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        GET /api/categories/{id}/stats/
        Статистика категории.
        """
        category = self.get_object()
        
        # Количество товаров в категории (включая подкатегории)
        products_count = category.products_count
        
        # Средняя цена
        products = category.get_all_products()
        avg_price = products.aggregate(avg=Avg('price'))['avg'] or 0
        
        # Количество поставщиков
        suppliers_count = products.values('supplier').distinct().count()
        
        return Response({
            'category_id': category.id,
            'category_name': category.name,
            'products_count': products_count,
            'avg_price': float(avg_price),
            'suppliers_count': suppliers_count,
            'breadcrumbs': category.get_breadcrumbs()
        })


class ProductImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet для изображений товаров.
    """
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticated, IsSupplierOrAdmin]
    
    def get_queryset(self):
        """
        Фильтрация изображений в зависимости от прав пользователя.
        """
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            return self.queryset.all()
        
        # Поставщик видит только изображения своих товаров
        if user.role == 'supplier':
            return self.queryset.filter(product__supplier=user)
        
        return ProductImage.objects.none()
    
    def perform_create(self, serializer):
        """
        Создание изображения товара.
        """
        product = serializer.validated_data['product']
        
        # Проверяем права на добавление изображений к товару
        if not (self.request.user.is_superuser or self.request.user.role == 'admin'):
            if product.supplier != self.request.user:
                raise PermissionError('У вас нет прав для добавления изображений к этому товару')
        
        serializer.save()


class ProductReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet для отзывов о товарах.
    """
    queryset = ProductReview.objects.all().select_related('product', 'user')
    serializer_class = ProductReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """
        Динамические разрешения в зависимости от действия.
        """
        if self.action in ['create', 'update', 'partial_update']:
            self.permission_classes = [IsAuthenticated]
        elif self.action == 'destroy':
            self.permission_classes = [IsAuthenticated, IsAdminUser]
        elif self.action == 'list':
            self.permission_classes = [IsAuthenticated]
        
        return super().get_permissions()
    
    def get_queryset(self):
        """
        Фильтрация отзывов.
        """
        user = self.request.user
        
        # Администраторы видят все отзывы
        if user.is_superuser or user.role == 'admin':
            return self.queryset.all()
        
        # Пользователи видят только одобренные отзывы
        return self.queryset.filter(is_approved=True)
    
    def perform_create(self, serializer):
        """
        Создание отзыва.
        """
        # Проверяем, не оставлял ли пользователь уже отзыв на этот товар
        product = serializer.validated_data['product']
        
        if ProductReview.objects.filter(product=product, user=self.request.user).exists():
            raise serializers.ValidationError('Вы уже оставляли отзыв на этот товар')
        
        # Автоматически одобряем отзывы от администраторов
        if self.request.user.is_superuser or self.request.user.role == 'admin':
            serializer.save(user=self.request.user, is_approved=True)
        else:
            serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        POST /api/reviews/{id}/approve/
        Одобрить отзыв.
        """
        if not request.user.is_superuser and request.user.role != 'admin':
            return Response(
                {'error': 'Только администраторы могут одобрять отзывы'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        review = self.get_object()
        review.is_approved = True
        review.save()
        
        return Response({'success': 'Отзыв одобрен'})


class SearchProductsView(APIView):
    """
    Поиск товаров.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/products/search/
        Поиск товаров по запросу.
        """
        query = request.query_params.get('q', '')
        category_id = request.query_params.get('category_id')
        supplier_id = request.query_params.get('supplier_id')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        in_stock = request.query_params.get('in_stock')
        
        if not query and not category_id and not supplier_id:
            return Response(
                {'error': 'Не указаны параметры поиска'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        products = search_products(
            user=request.user,
            query=query,
            category_id=category_id,
            supplier_id=supplier_id,
            min_price=min_price,
            max_price=max_price,
            in_stock=in_stock
        )
        
        # Пагинация
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_products = products[start:end]
        
        serializer = ProductSerializer(paginated_products, many=True)
        
        return Response({
            'query': query,
            'count': products.count(),
            'next': f"?q={query}&page={page + 1}&page_size={page_size}" if end < products.count() else None,
            'previous': f"?q={query}&page={page - 1}&page_size={page_size}" if page > 1 else None,
            'results': serializer.data
        })


class PopularProductsView(APIView):
    """
    Популярные товары.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/products/popular/
        Получить популярные товары.
        """
        limit = int(request.query_params.get('limit', 10))
        category_id = request.query_params.get('category_id')
        
        popular_products = get_popular_products(
            user=request.user,
            limit=limit,
            category_id=category_id
        )
        
        serializer = ProductSerializer(popular_products, many=True)
        return Response(serializer.data)


class RecommendedProductsView(APIView):
    """
    Рекомендованные товары.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/products/recommended/
        Получить рекомендованные товары.
        """
        limit = int(request.query_params.get('limit', 10))
        category_id = request.query_params.get('category_id')
        
        recommended_products = get_recommended_products(
            user=request.user,
            limit=limit,
            category_id=category_id
        )
        
        serializer = ProductSerializer(recommended_products, many=True)
        return Response(serializer.data)


class MyProductsView(APIView):
    """
    Товары текущего пользователя (для поставщиков).
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/products/my-products/
        Получить товары текущего пользователя (поставщика).
        """
        if request.user.role != 'supplier':
            return Response(
                {'error': 'Только для поставщиков'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        products = Product.objects.filter(supplier=request.user)
        
        # Фильтры
        status_filter = request.query_params.get('status')
        category_id = request.query_params.get('category_id')
        in_stock = request.query_params.get('in_stock')
        
        if status_filter:
            products = products.filter(status=status_filter)
        if category_id:
            products = products.filter(category_id=category_id)
        if in_stock is not None:
            if in_stock.lower() == 'true':
                products = products.filter(in_stock=True)
            elif in_stock.lower() == 'false':
                products = products.filter(in_stock=False)
        
        # Пагинация
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_products = products[start:end]
        
        serializer = ProductSerializer(paginated_products, many=True)
        
        return Response({
            'count': products.count(),
            'next': f"?page={page + 1}&page_size={page_size}" if end < products.count() else None,
            'previous': f"?page={page - 1}&page_size={page_size}" if page > 1 else None,
            'results': serializer.data
        })


class ExportProductsView(APIView):
    """
    Экспорт товаров в CSV.
    """
    permission_classes = [IsAuthenticated, IsAdminUser | IsSupplierOrAdmin]
    
    def get(self, request):
        """
        GET /api/products/export/
        Экспортировать товары в CSV.
        """
        # Определяем, чьи товары экспортировать
        user = request.user
        supplier_id = request.query_params.get('supplier_id')
        
        if user.role == 'supplier':
            # Поставщик может экспортировать только свои товары
            supplier_id = user.id
        elif supplier_id and (user.is_superuser or user.role == 'admin'):
            # Администратор может указать поставщика
            pass
        else:
            supplier_id = None
        
        # Экспортируем товары
        csv_data = export_products_to_csv(supplier_id)
        
        # Возвращаем CSV файл
        from django.http import HttpResponse
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="products.csv"'
        
        return response
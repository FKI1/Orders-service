from rest_framework import viewsets, status, filters, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, Avg, F
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse
import csv

from .models import Product, Category, ProductImage, ProductReview, ProductSpecification
from .serializers import (
    ProductSerializer,
    ProductDetailSerializer,
    CategorySerializer,
    ProductImageSerializer,
    ProductReviewSerializer,
    CreateProductSerializer,
    UpdateProductSerializer,
    ProductStatsSerializer,
    ProductListSerializer,
    ProductSpecificationSerializer,
    ProductSpecificationCreateSerializer,
    ProductSpecificationUpdateSerializer,
    ProductSpecificationDetailSerializer
)
from .permissions import (
    CanViewProduct,
    CanCreateProduct,
    CanUpdateProduct,
    CanDeleteProduct,
    IsSupplierOrAdmin,
    CanViewSpecification,
    CanCreateSpecification,
    CanUpdateSpecification,
    CanDeleteSpecification
)
from .filters import ProductFilter, CategoryFilter
from .services import (
    search_products,
    get_products_by_category,
    get_popular_products,
    get_recommended_products,
    update_product_stock,
    calculate_product_statistics,
    export_products_to_csv,
    create_product_specification,
    update_product_specification,
    get_product_specification
)


class ProductSpecificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления спецификацией товара.
    
    list: GET /api/products/specifications/
    create: POST /api/products/specifications/
    retrieve: GET /api/products/specifications/{id}/
    update: PUT /api/products/specifications/{id}/
    partial_update: PATCH /api/products/specifications/{id}/
    destroy: DELETE /api/products/specifications/{id}/
    """
    queryset = ProductSpecification.objects.all().select_related('product')
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return ProductSpecificationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ProductSpecificationUpdateSerializer
        elif self.action == 'retrieve':
            return ProductSpecificationDetailSerializer
        return ProductSpecificationSerializer
    
    def get_permissions(self):
        """Динамические разрешения в зависимости от действия"""
        if self.action == 'list':
            self.permission_classes = [IsAuthenticated, CanViewSpecification]
        elif self.action == 'retrieve':
            self.permission_classes = [IsAuthenticated, CanViewSpecification]
        elif self.action == 'create':
            self.permission_classes = [IsAuthenticated, CanCreateSpecification]
        elif self.action in ['update', 'partial_update']:
            self.permission_classes = [IsAuthenticated, CanUpdateSpecification]
        elif self.action == 'destroy':
            self.permission_classes = [IsAuthenticated, CanDeleteSpecification]
        else:
            self.permission_classes = [IsAuthenticated]
        
        return super().get_permissions()
    
    def get_queryset(self):
        """Фильтрация спецификаций в зависимости от прав пользователя"""
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            return self.queryset.all()
        
        # Поставщик видит только спецификации своих товаров
        if user.role == 'supplier':
            return self.queryset.filter(product__supplier=user)
        
        # Остальные пользователи видят спецификации активных товаров
        return self.queryset.filter(
            product__status=Product.ProductStatus.ACTIVE,
            product__in_stock=True
        )
    
    def perform_create(self, serializer):
        """Создание спецификации"""
        specification = serializer.save()
        
        # Логируем создание спецификации
        from apps.users.services import log_user_activity
        log_user_activity(
            user=self.request.user,
            activity_type='specification_create',
            description=f'Создана спецификация для товара {specification.product.name}',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata={'product_id': specification.product.id}
        )
    
    def perform_update(self, serializer):
        """Обновление спецификации"""
        specification = serializer.save()
        
        # Логируем обновление спецификации
        from apps.users.services import log_user_activity
        log_user_activity(
            user=self.request.user,
            activity_type='specification_update',
            description=f'Обновлена спецификация товара {specification.product.name}',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata={'product_id': specification.product.id}
        )
    
    @action(detail=False, methods=['get'])
    def by_product(self, request):
        """
        GET /api/products/specifications/by-product/?product_id=1
        Получить спецификацию по ID товара.
        """
        product_id = request.query_params.get('product_id')
        
        if not product_id:
            return Response(
                {'error': 'Не указан product_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            specification = ProductSpecification.objects.get(product_id=product_id)
            serializer = self.get_serializer(specification)
            return Response(serializer.data)
        except ProductSpecification.DoesNotExist:
            return Response(
                {'error': 'Спецификация для данного товара не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def by_supplier(self, request):
        """
        GET /api/products/specifications/by-supplier/
        Получить спецификации всех товаров поставщика.
        """
        if request.user.role != 'supplier' and not (request.user.is_superuser or request.user.role == 'admin'):
            return Response(
                {'error': 'Только для поставщиков и администраторов'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        supplier_id = request.query_params.get('supplier_id', request.user.id)
        
        specifications = self.queryset.filter(product__supplier_id=supplier_id)
        
        page = self.paginate_queryset(specifications)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(specifications, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """
        GET /api/products/specifications/{id}/export/
        Экспортировать спецификацию в JSON.
        """
        specification = self.get_object()
        data = specification.to_dict()
        
        # Добавляем основную информацию о товаре
        data['product'] = {
            'id': specification.product.id,
            'name': specification.product.name,
            'sku': specification.product.sku,
            'price': float(specification.product.price)
        }
        
        return Response(data)


class ProductSpecificationByProductView(generics.RetrieveAPIView):
    """
    Получение спецификации товара по slug товара.
    GET /api/products/{slug}/specification/
    """
    permission_classes = [AllowAny]
    serializer_class = ProductSpecificationDetailSerializer
    
    def get_object(self):
        slug = self.kwargs.get('slug')
        product = get_object_or_404(Product, slug=slug, status=Product.ProductStatus.ACTIVE)
        
        # Увеличиваем счетчик просмотров
        product.increment_views()
        
        # Получаем или создаем спецификацию
        specification, created = ProductSpecification.objects.get_or_create(product=product)
        
        return specification


class ProductSpecificationUpdateByProductView(generics.UpdateAPIView):
    """
    Обновление спецификации товара по slug товара.
    PUT/PATCH /api/products/{slug}/specification/update/
    """
    permission_classes = [IsAuthenticated, CanUpdateSpecification]
    serializer_class = ProductSpecificationUpdateSerializer
    
    def get_object(self):
        slug = self.kwargs.get('slug')
        product = get_object_or_404(Product, slug=slug)
        
        # Проверка прав на обновление
        user = self.request.user
        if not (user.is_superuser or user.role == 'admin' or product.supplier == user):
            self.permission_denied(
                self.request,
                message='У вас нет прав для обновления спецификации этого товара'
            )
        
        specification, created = ProductSpecification.objects.get_or_create(product=product)
        return specification
    
    def perform_update(self, serializer):
        specification = serializer.save()
        
        # Логируем обновление спецификации
        from apps.users.services import log_user_activity
        log_user_activity(
            user=self.request.user,
            activity_type='specification_update',
            description=f'Обновлена спецификация товара {specification.product.name}',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata={'product_id': specification.product.id, 'slug': specification.product.slug}
        )


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления товарами.
    """
    queryset = Product.objects.all().select_related(
        'category', 'supplier'
    ).prefetch_related('images', 'specification')
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'sku', 'short_description', 'description']
    ordering_fields = [
        'name', 'price', 'created_at', 'updated_at', 
        'rating', 'total_ordered', 'total_views'
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
        elif self.action == 'list':
            # Используем оптимизированный сериализатор для списка
            if self.request.query_params.get('compact') == 'true':
                return ProductListSerializer
        return ProductSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Переопределяем retrieve для увеличения счетчика просмотров"""
        instance = self.get_object()
        instance.increment_views()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        """
        Создание товара.
        """
        # Для поставщиков автоматически устанавливаем их как владельца
        if self.request.user.role == 'supplier':
            serializer.save(supplier=self.request.user)
        else:
            serializer.save()
        
        # Логируем создание товара
        from apps.users.services import log_user_activity
        product = serializer.instance
        log_user_activity(
            user=self.request.user,
            activity_type='product_create',
            description=f'Создан товар: {product.name}',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata={'product_id': product.id, 'sku': product.sku}
        )
    
    @action(detail=True, methods=['get'])
    def specification(self, request, pk=None):
        """
        GET /api/products/{id}/specification/
        Получить спецификацию товара.
        """
        product = self.get_object()
        
        try:
            specification = product.specification
            serializer = ProductSpecificationDetailSerializer(specification)
            return Response(serializer.data)
        except ProductSpecification.DoesNotExist:
            return Response(
                {'detail': 'Спецификация для данного товара не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post', 'put', 'patch'])
    def update_specification(self, request, pk=None):
        """
        POST/PUT/PATCH /api/products/{id}/update-specification/
        Создать или обновить спецификацию товара.
        """
        product = self.get_object()
        
        # Проверка прав
        user = request.user
        if not (user.is_superuser or user.role == 'admin' or product.supplier == user):
            return Response(
                {'error': 'У вас нет прав для изменения спецификации этого товара'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем или создаем спецификацию
        specification, created = ProductSpecification.objects.get_or_create(product=product)
        
        if request.method == 'POST' and not created:
            return Response(
                {'error': 'Спецификация уже существует. Используйте PUT для обновления.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Выбираем сериализатор
        serializer_class = ProductSpecificationCreateSerializer if created else ProductSpecificationUpdateSerializer
        serializer = serializer_class(specification, data=request.data, partial=request.method == 'PATCH')
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Логируем действие
        from apps.users.services import log_user_activity
        log_user_activity(
            user=user,
            activity_type='specification_create' if created else 'specification_update',
            description=f'{"Создана" if created else "Обновлена"} спецификация товара {product.name}',
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'product_id': product.id, 'created': created}
        )
        
        return Response(ProductSpecificationDetailSerializer(specification).data)
    
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
            
            # Логируем обновление остатков
            from apps.users.services import log_user_activity
            log_user_activity(
                user=request.user,
                activity_type='stock_update',
                description=f'Обновлен остаток товара {product.name}: {quantity}',
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'product_id': product.id, 'quantity': quantity}
            )
            
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
    
    @action(detail=False, methods=['get'])
    def new_arrivals(self, request):
        """
        GET /api/products/new-arrivals/
        Новинки (последние добавленные товары).
        """
        limit = int(request.query_params.get('limit', 10))
        
        products = self.get_queryset().filter(
            status=Product.ProductStatus.ACTIVE
        ).order_by('-created_at')[:limit]
        
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def bestsellers(self, request):
        """
        GET /api/products/bestsellers/
        Бестселлеры.
        """
        limit = int(request.query_params.get('limit', 10))
        category_id = request.query_params.get('category_id')
        
        queryset = self.get_queryset().filter(
            status=Product.ProductStatus.ACTIVE
        )
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        products = queryset.order_by('-total_ordered')[:limit]
        
        serializer = ProductListSerializer(products, many=True)
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
        has_specification = request.query_params.get('has_specification')
        sort_by = request.query_params.get('sort_by', 'popular')
        
        if min_price:
            products = products.filter(price__gte=min_price)
        if max_price:
            products = products.filter(price__lte=max_price)
        if in_stock and in_stock.lower() == 'true':
            products = products.filter(in_stock=True)
        if has_specification and has_specification.lower() == 'true':
            products = products.filter(specification__isnull=False)
        
        # Сортировка
        if sort_by == 'price_asc':
            products = products.order_by('price')
        elif sort_by == 'price_desc':
            products = products.order_by('-price')
        elif sort_by == 'newest':
            products = products.order_by('-created_at')
        elif sort_by == 'rating':
            products = products.order_by('-rating')
        elif sort_by == 'popular':
            products = products.order_by('-total_ordered')
        
        # Пагинация
        page = self.paginate_queryset(products)
        if page is not None:
            use_compact = request.query_params.get('compact') == 'true'
            serializer_class = ProductListSerializer if use_compact else ProductSerializer
            serializer = serializer_class(page, many=True)
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
        
        # Диапазон цен
        price_range = products.aggregate(
            min=Min('price'),
            max=Max('price')
        )
        
        # Количество поставщиков
        suppliers_count = products.values('supplier').distinct().count()
        
        # Товары с низким остатком
        low_stock_count = products.filter(
            stock_quantity__lte=F('min_stock_level')
        ).count()
        
        return Response({
            'category_id': category.id,
            'category_name': category.name,
            'products_count': products_count,
            'avg_price': float(avg_price),
            'min_price': float(price_range['min']) if price_range['min'] else 0,
            'max_price': float(price_range['max']) if price_range['max'] else 0,
            'suppliers_count': suppliers_count,
            'low_stock_count': low_stock_count,
            'breadcrumbs': category.get_breadcrumbs()
        })


class ProductImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet для изображений товаров.
    """
    queryset = ProductImage.objects.all().select_related('product')
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
        
        # Логируем создание изображения
        from apps.users.services import log_user_activity
        log_user_activity(
            user=self.request.user,
            activity_type='product_image_add',
            description=f'Добавлено изображение для товара {product.name}',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata={'product_id': product.id}
        )
    
    @action(detail=True, methods=['post'])
    def set_main(self, request, pk=None):
        """
        POST /api/product-images/{id}/set-main/
        Установить изображение как основное.
        """
        image = self.get_object()
        image.is_main = True
        image.save()
        
        return Response({'success': 'Изображение установлено как основное'})


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
        
        # Логируем создание отзыва
        from apps.users.services import log_user_activity
        log_user_activity(
            user=self.request.user,
            activity_type='review_create',
            description=f'Добавлен отзыв на товар {product.name}',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata={'product_id': product.id, 'rating': serializer.validated_data['rating']}
        )
    
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
        
        # Обновляем рейтинг товара
        review.update_product_rating()
        
        return Response({'success': 'Отзыв одобрен'})
    
    @action(detail=True, methods=['post'])
    def helpful(self, request, pk=None):
        """
        POST /api/reviews/{id}/helpful/
        Отметить отзыв как полезный.
        """
        review = self.get_object()
        review.helpful_yes += 1
        review.save()
        
        return Response({
            'success': 'Отзыв отмечен как полезный',
            'helpful_yes': review.helpful_yes,
            'helpful_no': review.helpful_no
        })
    
    @action(detail=True, methods=['post'])
    def not_helpful(self, request, pk=None):
        """
        POST /api/reviews/{id}/not-helpful/
        Отметить отзыв как бесполезный.
        """
        review = self.get_object()
        review.helpful_no += 1
        review.save()
        
        return Response({
            'success': 'Отзыв отмечен как бесполезный',
            'helpful_yes': review.helpful_yes,
            'helpful_no': review.helpful_no
        })


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
        has_specification = request.query_params.get('has_specification')
        
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
            in_stock=in_stock,
            has_specification=has_specification
        )
        
        # Пагинация
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_products = products[start:end]
        
        # Выбор сериализатора
        use_compact = request.query_params.get('compact') == 'true'
        serializer_class = ProductListSerializer if use_compact else ProductSerializer
        serializer = serializer_class(paginated_products, many=True)
        
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
        
        use_compact = request.query_params.get('compact') == 'true'
        serializer_class = ProductListSerializer if use_compact else ProductSerializer
        serializer = serializer_class(popular_products, many=True)
        
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
        
        use_compact = request.query_params.get('compact') == 'true'
        serializer_class = ProductListSerializer if use_compact else ProductSerializer
        serializer = serializer_class(recommended_products, many=True)
        
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
        
        products = Product.objects.filter(supplier=request.user).select_related(
            'category'
        ).prefetch_related('images', 'specification')
        
        # Фильтры
        status_filter = request.query_params.get('status')
        category_id = request.query_params.get('category_id')
        in_stock = request.query_params.get('in_stock')
        has_specification = request.query_params.get('has_specification')
        
        if status_filter:
            products = products.filter(status=status_filter)
        if category_id:
            products = products.filter(category_id=category_id)
        if in_stock is not None:
            if in_stock.lower() == 'true':
                products = products.filter(in_stock=True)
            elif in_stock.lower() == 'false':
                products = products.filter(in_stock=False)
        if has_specification is not None:
            if has_specification.lower() == 'true':
                products = products.filter(specification__isnull=False)
            elif has_specification.lower() == 'false':
                products = products.filter(specification__isnull=True)
        
        # Пагинация
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_products = products[start:end]
        
        use_compact = request.query_params.get('compact') == 'true'
        serializer_class = ProductListSerializer if use_compact else ProductSerializer
        serializer = serializer_class(paginated_products, many=True)
        
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
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="products.csv"'
        
        return response
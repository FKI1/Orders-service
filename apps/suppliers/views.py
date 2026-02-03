from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg, Sum, F
from django.utils import timezone
from datetime import timedelta

from apps.users.models import User
from apps.orders.models import Order, OrderItem
from apps.products.models import Product
from .serializers import (
    SupplierSerializer,
    SupplierProfileSerializer,
    SupplierOrderSerializer,
    SupplierProductSerializer,
    SupplierPerformanceSerializer,
    CreateSupplierSerializer,
    UpdateSupplierSerializer
)
from .filters import SupplierFilter
from .services import (
    get_supplier_statistics,
    calculate_supplier_rating,
    get_supplier_orders_summary,
    generate_supplier_report
)


class SupplierViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления поставщиками.
    Доступно только администраторам.
    """
    queryset = User.objects.filter(role='supplier').select_related('profile')
    serializer_class = SupplierSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SupplierFilter
    search_fields = ['email', 'first_name', 'last_name', 'company_name']
    ordering_fields = ['date_joined', 'company_name']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateSupplierSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateSupplierSerializer
        return SupplierSerializer
    
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """
        GET /api/suppliers/{id}/performance/
        Статистика производительности поставщика.
        """
        supplier = self.get_object()
        performance_data = get_supplier_statistics(supplier)
        serializer = SupplierPerformanceSerializer(performance_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """
        GET /api/suppliers/{id}/products/
        Товары поставщика.
        """
        supplier = self.get_object()
        products = Product.objects.filter(supplier=supplier)
        
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = SupplierProductSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SupplierProductSerializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def orders(self, request, pk=None):
        """
        GET /api/suppliers/{id}/orders/
        Заказы поставщика.
        """
        supplier = self.get_object()
        orders = Order.objects.filter(
            items__product__supplier=supplier
        ).distinct().order_by('-created_at')
        
        page = self.paginate_queryset(orders)
        if page is not None:
            serializer = SupplierOrderSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = SupplierOrderSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        POST /api/suppliers/{id}/activate/
        Активировать поставщика.
        """
        supplier = self.get_object()
        supplier.is_active = True
        supplier.save()
        return Response({'status': 'Поставщик активирован'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        POST /api/suppliers/{id}/deactivate/
        Деактивировать поставщика.
        """
        supplier = self.get_object()
        supplier.is_active = False
        supplier.save()
        return Response({'status': 'Поставщик деактивирован'})
    
    @action(detail=True, methods=['post'])
    def generate_report(self, request, pk=None):
        """
        POST /api/suppliers/{id}/generate-report/
        Сгенерировать отчет по поставщику.
        """
        supplier = self.get_object()
        date_from = request.data.get('date_from')
        date_to = request.data.get('date_to', timezone.now().date())
        
        report = generate_supplier_report(supplier, date_from, date_to)
        return Response(report)


class MySupplierProfileView(APIView):
    """
    Профиль текущего поставщика.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/suppliers/me/
        Получить профиль текущего поставщика.
        """
        if request.user.role != 'supplier':
            return Response(
                {'error': 'Только для поставщиков'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SupplierProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request):
        """
        PUT /api/suppliers/me/
        Обновить профиль поставщика.
        """
        if request.user.role != 'supplier':
            return Response(
                {'error': 'Только для поставщиков'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SupplierProfileSerializer(
            request.user, 
            data=request.data, 
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)


class SupplierOrdersView(APIView):
    """
    Заказы текущего поставщика.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/suppliers/me/orders/
        Получить заказы текущего поставщика.
        """
        if request.user.role != 'supplier':
            return Response(
                {'error': 'Только для поставщиков'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем параметры запроса
        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        ordering = request.query_params.get('ordering', '-created_at')
        
        # Базовый queryset
        orders = Order.objects.filter(
            items__product__supplier=request.user
        ).distinct()
        
        # Применяем фильтры
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        if date_from:
            orders = orders.filter(created_at__date__gte=date_from)
        
        if date_to:
            orders = orders.filter(created_at__date__lte=date_to)
        
        # Сортировка
        orders = orders.order_by(ordering)
        
        # Пагинация (простая)
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_orders = orders[start:end]
        
        serializer = SupplierOrderSerializer(
            paginated_orders, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'count': orders.count(),
            'next': f"?page={page + 1}&page_size={page_size}" if end < orders.count() else None,
            'previous': f"?page={page - 1}&page_size={page_size}" if page > 1 else None,
            'results': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        GET /api/suppliers/me/orders/summary/
        Сводка по заказам поставщика.
        """
        if request.user.role != 'supplier':
            return Response(
                {'error': 'Только для поставщиков'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        summary = get_supplier_orders_summary(request.user)
        return Response(summary)


class SupplierProductsView(APIView):
    """
    Товары текущего поставщика.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/suppliers/me/products/
        Получить товары текущего поставщика.
        """
        if request.user.role != 'supplier':
            return Response(
                {'error': 'Только для поставщиков'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        products = Product.objects.filter(supplier=request.user)
        
        # Фильтры
        search = request.query_params.get('search')
        category_id = request.query_params.get('category_id')
        in_stock = request.query_params.get('in_stock')
        
        if search:
            products = products.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(description__icontains=search)
            )
        
        if category_id:
            products = products.filter(category_id=category_id)
        
        if in_stock is not None:
            if in_stock.lower() == 'true':
                products = products.filter(in_stock=True)
            elif in_stock.lower() == 'false':
                products = products.filter(in_stock=False)
        
        # Сортировка
        ordering = request.query_params.get('ordering', 'name')
        products = products.order_by(ordering)
        
        # Пагинация
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_products = products[start:end]
        
        serializer = SupplierProductSerializer(
            paginated_products, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'count': products.count(),
            'next': f"?page={page + 1}&page_size={page_size}" if end < products.count() else None,
            'previous': f"?page={page - 1}&page_size={page_size}" if page > 1 else None,
            'results': serializer.data
        })
    
    def post(self, request):
        """
        POST /api/suppliers/me/products/
        Добавить новый товар.
        """
        if request.user.role != 'supplier':
            return Response(
                {'error': 'Только для поставщиков'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SupplierProductSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # Добавляем поставщика (текущего пользователя)
        product = serializer.save(supplier=request.user)
        
        return Response(
            SupplierProductSerializer(product, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class SupplierDashboardView(APIView):
    """
    Дашборд поставщика.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/suppliers/me/dashboard/
        Дашборд поставщика с основной статистикой.
        """
        if request.user.role != 'supplier':
            return Response(
                {'error': 'Только для поставщиков'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        supplier = request.user
        today = timezone.now().date()
        
        # Статистика за сегодня
        today_orders = Order.objects.filter(
            items__product__supplier=supplier,
            created_at__date=today
        ).distinct()
        
        today_count = today_orders.count()
        today_amount = today_orders.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Статистика за текущий месяц
        first_day = today.replace(day=1)
        month_orders = Order.objects.filter(
            items__product__supplier=supplier,
            created_at__date__gte=first_day
        ).distinct()
        
        month_count = month_orders.count()
        month_amount = month_orders.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Количество товаров
        products_count = Product.objects.filter(supplier=supplier).count()
        
        # Товары с низким остатком
        low_stock_products = Product.objects.filter(
            supplier=supplier,
            in_stock=True,
            stock_quantity__lte=F('min_stock_level')
        ).count()
        
        # Заказы по статусам
        status_counts = Order.objects.filter(
            items__product__supplier=supplier
        ).values('status').annotate(
            count=Count('id', distinct=True)
        )
        
        status_summary = {
            item['status']: item['count']
            for item in status_counts
        }
        
        # Последние заказы
        recent_orders = Order.objects.filter(
            items__product__supplier=supplier
        ).distinct().order_by('-created_at')[:5]
        
        recent_orders_data = SupplierOrderSerializer(
            recent_orders, 
            many=True, 
            context={'request': request}
        ).data
        
        # Популярные товары
        popular_products = Product.objects.filter(
            supplier=supplier,
            order_items__isnull=False
        ).annotate(
            total_sold=Sum('order_items__quantity'),
            total_revenue=Sum('order_items__total')
        ).order_by('-total_sold')[:5]
        
        popular_products_data = []
        for product in popular_products:
            popular_products_data.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'total_sold': product.total_sold or 0,
                'total_revenue': product.total_revenue or 0
            })
        
        return Response({
            'today': {
                'orders_count': today_count,
                'orders_amount': float(today_amount)
            },
            'month': {
                'orders_count': month_count,
                'orders_amount': float(month_amount)
            },
            'products': {
                'total_count': products_count,
                'low_stock_count': low_stock_products
            },
            'orders_by_status': status_summary,
            'recent_orders': recent_orders_data,
            'popular_products': popular_products_data,
            'timestamp': timezone.now().isoformat()
        })


class SupplierPublicView(APIView):
    """
    Публичная информация о поставщиках.
    Доступна всем авторизованным пользователям.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/suppliers/public/
        Список активных поставщиков для закупщиков.
        """
        suppliers = User.objects.filter(
            role='supplier',
            is_active=True
        ).select_related('profile')
        
        # Фильтры
        search = request.query_params.get('search')
        min_rating = request.query_params.get('min_rating')
        
        if search:
            suppliers = suppliers.filter(
                Q(company_name__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        # Пагинация
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_suppliers = suppliers[start:end]
        
        # Рассчитываем рейтинг для каждого поставщика
        suppliers_data = []
        for supplier in paginated_suppliers:
            rating = calculate_supplier_rating(supplier)
            
            # Фильтр по минимальному рейтингу
            if min_rating and rating < float(min_rating):
                continue
            
            suppliers_data.append({
                'id': supplier.id,
                'company_name': supplier.company_name,
                'email': supplier.email,
                'contact_phone': supplier.phone,
                'rating': rating,
                'product_count': Product.objects.filter(supplier=supplier).count(),
                'is_active': supplier.is_active
            })
        
        return Response({
            'count': suppliers.count(),
            'next': f"?page={page + 1}&page_size={page_size}" if end < suppliers.count() else None,
            'previous': f"?page={page - 1}&page_size={page_size}" if page > 1 else None,
            'results': suppliers_data
        })
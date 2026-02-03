from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Sum, Count, Avg, Q, F
from django.db import connection
from django.http import HttpResponse
import json

from apps.orders.models import Order, OrderItem
from apps.products.models import Product
from apps.users.models import User
from .serializers import (
    OrderStatsSerializer,
    BudgetReportSerializer,
    TopProductsSerializer,
    SalesTrendSerializer,
    SupplierAnalyticsSerializer
)
from .services import (
    calculate_order_stats,
    get_budget_report,
    get_top_products,
    get_sales_trend,
    get_supplier_analytics,
    generate_daily_report,
    export_to_excel
)
from .reports import generate_pdf_report, generate_excel_report


class AnalyticsViewSet(ViewSet):
    """
    ViewSet для аналитики заказов.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Базовый queryset в зависимости от роли пользователя"""
        user = self.request.user
        
        if user.role == 'admin':
            return Order.objects.all()
        elif user.role in ['network_admin', 'store_manager', 'buyer']:
            # Возвращаем заказы, связанные с пользователем
            return Order.objects.filter(
                Q(created_by=user) | 
                Q(store__manager=user) |
                Q(store__network__employees=user)
            ).distinct()
        elif user.role == 'supplier':
            # Заказы с товарами поставщика
            return Order.objects.filter(
                items__product__supplier=user
            ).distinct()
        
        return Order.objects.none()
    
    @action(detail=False, methods=['get'])
    def orders_stats(self, request):
        """
        GET /api/analytics/orders-stats/
        Статистика заказов за период.
        
        Query Parameters:
        - period: day/week/month/year/custom
        - date_from: YYYY-MM-DD (для custom)
        - date_to: YYYY-MM-DD (для custom)
        - store_id: фильтр по магазину
        - network_id: фильтр по сети
        """
        period = request.query_params.get('period', 'month')
        store_id = request.query_params.get('store_id')
        network_id = request.query_params.get('network_id')
        
        # Определяем даты периода
        end_date = timezone.now()
        
        if period == 'day':
            start_date = end_date - timedelta(days=1)
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'year':
            start_date = end_date - timedelta(days=365)
        elif period == 'custom':
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to', end_date.date())
            
            if date_from:
                start_date = datetime.strptime(date_from, '%Y-%m-%d')
                end_date = datetime.strptime(date_to, '%Y-%m-%d')
            else:
                start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Фильтруем заказы
        queryset = self.get_queryset().filter(
            created_at__date__range=[start_date.date(), end_date.date()]
        )
        
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        if network_id:
            queryset = queryset.filter(store__network_id=network_id)
        
        # Рассчитываем статистику
        stats = calculate_order_stats(queryset, start_date, end_date, period)
        
        serializer = OrderStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def budget(self, request):
        """
        GET /api/analytics/budget/
        Отчет по остаткам бюджета.
        """
        user = request.user
        
        if user.role not in ['network_admin', 'store_manager', 'buyer']:
            return Response(
                {'error': 'Отчет доступен только для сотрудников сетей'},
                status=403
            )
        
        # Получаем отчет по бюджету
        budget_report = get_budget_report(user)
        
        serializer = BudgetReportSerializer(budget_report)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def top_products(self, request):
        """
        GET /api/analytics/top-products/
        Топ товаров по продажам.
        
        Query Parameters:
        - limit: количество товаров (default: 10)
        - period: day/week/month/year
        - category_id: фильтр по категории
        """
        limit = int(request.query_params.get('limit', 10))
        period = request.query_params.get('period', 'month')
        category_id = request.query_params.get('category_id')
        
        top_products = get_top_products(
            user=request.user,
            limit=limit,
            period=period,
            category_id=category_id
        )
        
        serializer = TopProductsSerializer(top_products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def sales_trend(self, request):
        """
        GET /api/analytics/sales-trend/
        Динамика продаж по дням/неделям/месяцам.
        """
        period = request.query_params.get('period', 'month')
        days = int(request.query_params.get('days', 30))
        
        trend = get_sales_trend(request.user, period, days)
        
        serializer = SalesTrendSerializer(trend, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def supplier_performance(self, request):
        """
        GET /api/analytics/supplier-performance/
        Аналитика по поставщикам (только для администраторов и закупщиков).
        """
        if request.user.role not in ['admin', 'buyer', 'network_admin']:
            return Response(
                {'error': 'Недостаточно прав'},
                status=403
            )
        
        suppliers_data = get_supplier_analytics(request.user)
        
        serializer = SupplierAnalyticsSerializer(suppliers_data, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def daily_report(self, request):
        """
        GET /api/analytics/daily-report/
        Ежедневный отчет по заказам.
        """
        date = request.query_params.get('date', timezone.now().date())
        
        report = generate_daily_report(request.user, date)
        
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """
        GET /api/analytics/export-excel/
        Экспорт аналитики в Excel.
        
        Query Parameters:
        - report_type: orders/products/suppliers
        - date_from: YYYY-MM-DD
        - date_to: YYYY-MM-DD
        """
        report_type = request.query_params.get('report_type', 'orders')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Генерируем Excel файл
        excel_file = export_to_excel(
            user=request.user,
            report_type=report_type,
            date_from=date_from,
            date_to=date_to
        )
        
        # Возвращаем файл как ответ
        response = HttpResponse(
            excel_file,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="report_{report_type}.xlsx"'
        
        return response
    
    @action(detail=False, methods=['post'])
    def custom_report(self, request):
        """
        POST /api/analytics/custom-report/
        Кастомный отчет с фильтрами.
        
        Request Body:
        {
            "metrics": ["total_orders", "total_amount", "avg_order_value"],
            "dimensions": ["store", "product_category", "supplier"],
            "filters": {
                "date_from": "2024-01-01",
                "date_to": "2024-01-31",
                "status": ["approved", "delivered"]
            },
            "group_by": "day"  # day/week/month
        }
        """
        try:
            data = request.data
            metrics = data.get('metrics', [])
            dimensions = data.get('dimensions', [])
            filters = data.get('filters', {})
            group_by = data.get('group_by', 'day')
            
            queryset = self.get_queryset()
            
            # Применяем фильтры
            if 'date_from' in filters:
                queryset = queryset.filter(created_at__date__gte=filters['date_from'])
            if 'date_to' in filters:
                queryset = queryset.filter(created_at__date__lte=filters['date_to'])
            if 'status' in filters:
                queryset = queryset.filter(status__in=filters['status'])
            if 'store_id' in filters:
                queryset = queryset.filter(store_id=filters['store_id'])
            
            report_data = self._build_custom_report(
                queryset, metrics, dimensions, group_by
            )
            
            return Response(report_data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=400
            )
    
    def _build_custom_report(self, queryset, metrics, dimensions, group_by):
        """Вспомогательный метод для построения кастомного отчета"""
        # Упрощенная реализация
        report = {
            'metadata': {
                'metrics': metrics,
                'dimensions': dimensions,
                'group_by': group_by,
                'total_records': queryset.count()
            },
            'data': []
        }
        
        # Базовая агрегация
        if 'total_orders' in metrics:
            report['total_orders'] = queryset.count()
        
        if 'total_amount' in metrics:
            report['total_amount'] = queryset.aggregate(
                total=Sum('total_amount')
            )['total'] or 0
        
        if 'avg_order_value' in metrics:
            total = queryset.aggregate(total=Sum('total_amount'))['total'] or 0
            count = queryset.count()
            report['avg_order_value'] = total / count if count > 0 else 0
        
        return report


class RealTimeAnalyticsView(APIView):
    """
    Real-time аналитика (для дашбордов).
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/analytics/realtime/
        Real-time данные для дашборда.
        """
        user = request.user
        
        # Текущие показатели
        today = timezone.now().date()
        
        # Количество заказов сегодня
        today_orders = Order.objects.filter(
            created_at__date=today,
            created_by=user
        ).count()
        
        # Сумма заказов сегодня
        today_amount = Order.objects.filter(
            created_at__date=today,
            created_by=user
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Заказов в работе
        active_orders = Order.objects.filter(
            created_by=user,
            status__in=['pending', 'approved', 'processing']
        ).count()
        
        # Товаров в корзине
        cart_items_count = 0
        if hasattr(user, 'cart'):
            cart_items_count = user.cart.items.count()
        
        # Последние заказы
        recent_orders = Order.objects.filter(
            created_by=user
        ).order_by('-created_at')[:5].values(
            'id', 'order_number', 'status', 'total_amount', 'created_at'
        )
        
        return Response({
            'today_orders': today_orders,
            'today_amount': today_amount,
            'active_orders': active_orders,
            'cart_items_count': cart_items_count,
            'recent_orders': list(recent_orders),
            'timestamp': timezone.now().isoformat()
        })
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, Avg, F
from django.utils import timezone
from datetime import timedelta

from .models import Order, OrderItem, OrderHistory, Payment
from .serializers import (
    OrderSerializer,
    OrderDetailSerializer,
    OrderItemSerializer,
    CreateOrderSerializer,
    UpdateOrderSerializer,
    OrderStatusSerializer,
    OrderHistorySerializer,
    PaymentSerializer,
    CreatePaymentSerializer,
    OrderStatsSerializer
)
from .permissions import (
    CanViewOrder,
    CanCreateOrder,
    CanUpdateOrder,
    CanDeleteOrder,
    CanApproveOrder,
    CanCancelOrder
)
from .filters import OrderFilter
from .services import (
    create_order_from_cart,
    approve_order,
    cancel_order,
    update_order_status,
    create_order_history,
    calculate_order_statistics
)


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления заказами.
    """
    queryset = Order.objects.all().select_related(
        'store', 'created_by', 'approved_by'
    ).prefetch_related('items', 'items__product')
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OrderFilter
    search_fields = ['order_number', 'notes']
    ordering_fields = [
        'created_at', 'updated_at', 'total_amount', 
        'required_delivery_date'
    ]
    
    def get_permissions(self):
        """
        Динамические разрешения в зависимости от действия.
        """
        if self.action == 'list':
            self.permission_classes = [IsAuthenticated, CanViewOrder]
        elif self.action == 'retrieve':
            self.permission_classes = [IsAuthenticated, CanViewOrder]
        elif self.action == 'create':
            self.permission_classes = [IsAuthenticated, CanCreateOrder]
        elif self.action in ['update', 'partial_update']:
            self.permission_classes = [IsAuthenticated, CanUpdateOrder]
        elif self.action == 'destroy':
            self.permission_classes = [IsAuthenticated, CanDeleteOrder]
        else:
            self.permission_classes = [IsAuthenticated]
        
        return super().get_permissions()
    
    def get_queryset(self):
        """
        Фильтрация заказов в зависимости от роли пользователя.
        """
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            return self.queryset.all()
        
        # Сотрудник сети видит заказы своей сети
        if user.role in ['network_admin', 'store_manager', 'buyer']:
            # Заказы магазинов, где пользователь сотрудник
            from apps.networks.models import StoreAssignment
            user_stores = StoreAssignment.objects.filter(
                user=user
            ).values_list('store_id', flat=True)
            
            return self.queryset.filter(
                Q(store__network__employees=user) |
                Q(store__manager=user) |
                Q(store_id__in=user_stores) |
                Q(created_by=user)
            ).distinct()
        
        return Order.objects.none()
    
    def get_serializer_class(self):
        """
        Выбор сериализатора в зависимости от действия.
        """
        if self.action == 'create':
            return CreateOrderSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateOrderSerializer
        elif self.action == 'retrieve':
            return OrderDetailSerializer
        return OrderSerializer
    
    def perform_create(self, serializer):
        """
        Создание заказа с историей.
        """
        order = serializer.save(created_by=self.request.user)
        
        # Создаем запись в истории
        create_order_history(
            order=order,
            user=self.request.user,
            action='Создан заказ',
            description=f'Создан новый заказ {order.order_number}'
        )
    
    def perform_update(self, serializer):
        """
        Обновление заказа с историей изменений.
        """
        old_order = self.get_object()
        order = serializer.save()
        
        # Отслеживаем изменения статуса
        if old_order.status != order.status:
            create_order_history(
                order=order,
                user=self.request.user,
                action='Изменен статус',
                field='status',
                old_value=old_order.status,
                new_value=order.status,
                description=f'Статус изменен с {old_order.get_status_display()} на {order.get_status_display()}'
            )
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        POST /api/orders/{id}/approve/
        Подтвердить заказ.
        """
        order = self.get_object()
        
        # Проверяем права
        if not request.user.has_perm('orders.can_approve_order'):
            return Response(
                {'error': 'У вас нет прав для подтверждения заказов'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            approved_order = approve_order(order, request.user)
            return Response(
                OrderSerializer(approved_order).data,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        POST /api/orders/{id}/cancel/
        Отменить заказ.
        """
        order = self.get_object()
        reason = request.data.get('reason', '')
        
        try:
            cancelled_order = cancel_order(order, request.user, reason)
            return Response(
                OrderSerializer(cancelled_order).data,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['patch'])
    def status(self, request, pk=None):
        """
        PATCH /api/orders/{id}/status/
        Изменить статус заказа.
        """
        order = self.get_object()
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        new_status = serializer.validated_data['status']
        comment = serializer.validated_data.get('comment', '')
        
        try:
            updated_order = update_order_status(
                order=order,
                user=request.user,
                new_status=new_status,
                comment=comment
            )
            return Response(
                OrderSerializer(updated_order).data,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        GET /api/orders/{id}/history/
        Получить историю заказа.
        """
        order = self.get_object()
        history = order.history.all().order_by('-created_at')
        
        page = self.paginate_queryset(history)
        if page is not None:
            serializer = OrderHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = OrderHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """
        GET /api/orders/{id}/items/
        Получить товары в заказе.
        """
        order = self.get_object()
        items = order.items.all().select_related('product')
        
        page = self.paginate_queryset(items)
        if page is not None:
            serializer = OrderItemSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = OrderItemSerializer(items, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        GET /api/orders/{id}/stats/
        Статистика заказа.
        """
        order = self.get_object()
        stats = {
            'order_number': order.order_number,
            'items_count': order.items_count,
            'total_quantity': order.total_quantity,
            'subtotal': float(order.subtotal),
            'discount_amount': float(order.discount_amount),
            'total_amount': float(order.total_amount),
            'paid_amount': float(order.paid_amount),
            'remaining_amount': float(order.remaining_amount),
            'created_at': order.created_at,
            'status': order.status,
            'payment_status': order.payment_status
        }
        return Response(stats)
    
    @action(detail=False, methods=['post'])
    def from_cart(self, request):
        """
        POST /api/orders/from-cart/
        Создать заказ из корзины.
        """
        store_id = request.data.get('store_id')
        delivery_date = request.data.get('delivery_date')
        notes = request.data.get('notes', '')
        
        try:
            order = create_order_from_cart(
                user=request.user,
                store_id=store_id,
                delivery_date=delivery_date,
                notes=notes
            )
            return Response(
                OrderSerializer(order).data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class OrderItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления позициями заказа.
    """
    queryset = OrderItem.objects.all().select_related('product', 'order')
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Фильтрация позиций заказа в зависимости от прав пользователя.
        """
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            return self.queryset.all()
        
        # Только позиции заказов, к которым у пользователя есть доступ
        from .permissions import CanViewOrder
        permission = CanViewOrder()
        
        accessible_order_ids = []
        for order in Order.objects.all():
            if permission.has_object_permission(self.request, self, order):
                accessible_order_ids.append(order.id)
        
        return self.queryset.filter(order_id__in=accessible_order_ids)
    
    def perform_create(self, serializer):
        """
        Создание позиции в заказе.
        """
        order = serializer.validated_data['order']
        
        # Проверяем права на добавление товаров в заказ
        if not self.request.user.has_perm('orders.can_update_order'):
            if order.created_by != self.request.user:
                raise PermissionError('У вас нет прав для добавления товаров в этот заказ')
        
        serializer.save()


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления платежами.
    """
    queryset = Payment.objects.all().select_related('order', 'created_by')
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreatePaymentSerializer
        return PaymentSerializer
    
    def get_queryset(self):
        """
        Фильтрация платежей в зависимости от роли пользователя.
        """
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            return self.queryset.all()
        
        # Платежи заказов, к которым у пользователя есть доступ
        from .permissions import CanViewOrder
        permission = CanViewOrder()
        
        accessible_order_ids = []
        for order in Order.objects.all():
            if permission.has_object_permission(self.request, self, order):
                accessible_order_ids.append(order.id)
        
        return self.queryset.filter(order_id__in=accessible_order_ids)
    
    def perform_create(self, serializer):
        """
        Создание платежа.
        """
        order = serializer.validated_data['order']
        
        # Проверяем права на создание платежей
        if not (user.is_superuser or user.role == 'admin'):
            if order.created_by != self.request.user:
                raise PermissionError('У вас нет прав для создания платежей по этому заказу')
        
        payment = serializer.save(created_by=self.request.user)
        
        # Создаем запись в истории заказа
        create_order_history(
            order=order,
            user=self.request.user,
            action='Добавлен платеж',
            description=f'Добавлен платеж {payment.payment_number} на сумму {payment.amount}'
        )


class OrderStatsView(APIView):
    """
    Статистика заказов.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/orders/stats/
        Получить статистику заказов.
        """
        user = request.user
        period = request.query_params.get('period', 'month')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        stats = calculate_order_statistics(
            user=user,
            period=period,
            date_from=date_from,
            date_to=date_to
        )
        
        serializer = OrderStatsSerializer(stats)
        return Response(serializer.data)


class MyOrdersView(APIView):
    """
    Заказы текущего пользователя.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/orders/my-orders/
        Получить заказы текущего пользователя.
        """
        user = request.user
        
        if user.is_superuser or user.role == 'admin':
            orders = Order.objects.all()
        else:
            orders = Order.objects.filter(created_by=user)
        
        # Фильтры
        status_filter = request.query_params.get('status')
        store_id = request.query_params.get('store_id')
        
        if status_filter:
            orders = orders.filter(status=status_filter)
        if store_id:
            orders = orders.filter(store_id=store_id)
        
        # Пагинация
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_orders = orders[start:end]
        
        serializer = OrderSerializer(paginated_orders, many=True)
        
        return Response({
            'count': orders.count(),
            'next': f"?page={page + 1}&page_size={page_size}" if end < orders.count() else None,
            'previous': f"?page={page - 1}&page_size={page_size}" if page > 1 else None,
            'results': serializer.data
        })
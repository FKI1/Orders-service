from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from datetime import timedelta, datetime
from .models import Order, OrderItem, OrderHistory


def create_order_from_cart(user, store_id, delivery_date, notes=''):
    """
    Создать заказ из корзины пользователя.
    """
    from apps.cart.models import Cart, CartItem
    from apps.networks.models import Store
    
    # Получаем корзину пользователя
    try:
        cart = Cart.objects.get(user=user)
    except Cart.DoesNotExist:
        raise ValueError('Корзина не найдена')
    
    if not cart.items.exists():
        raise ValueError('Корзина пуста')
    
    # Получаем магазин
    try:
        store = Store.objects.get(id=store_id)
    except Store.DoesNotExist:
        raise ValueError('Магазин не найден')
    
    # Создаем заказ
    order = Order.objects.create(
        store=store,
        created_by=user,
        required_delivery_date=delivery_date,
        notes=notes
    )
    
    # Переносим товары из корзины в заказ
    total_amount = 0
    for cart_item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            quantity=cart_item.quantity,
            unit_price=cart_item.product.price,
            total=cart_item.product.price * cart_item.quantity
        )
        total_amount += cart_item.product.price * cart_item.quantity
    
    # Обновляем суммы заказа
    order.subtotal = total_amount
    order.total_amount = total_amount
    order.save()
    
    # Очищаем корзину
    cart.items.all().delete()
    
    # Создаем запись в истории
    create_order_history(
        order=order,
        user=user,
        action='Создан из корзины',
        description='Заказ создан из корзины пользователя'
    )
    
    return order


def approve_order(order, user):
    """
    Подтвердить заказ.
    """
    if order.status != Order.Status.PENDING:
        raise ValueError('Можно подтверждать только заказы на согласовании')
    
    order.status = Order.Status.APPROVED
    order.approved_by = user
    order.approved_at = timezone.now()
    order.save()
    
    # Создаем запись в истории
    create_order_history(
        order=order,
        user=user,
        action='Заказ подтвержден',
        description=f'Заказ подтвержден пользователем {user.get_full_name()}'
    )
    
    return order


def cancel_order(order, user, reason=''):
    """
    Отменить заказ.
    """
    if not order.can_be_cancelled:
        raise ValueError('Этот заказ нельзя отменить')
    
    order.status = Order.Status.CANCELLED
    order.cancellation_reason = reason
    order.cancelled_at = timezone.now()
    order.save()
    
    # Создаем запись в истории
    create_order_history(
        order=order,
        user=user,
        action='Заказ отменен',
        description=f'Заказ отменен. Причина: {reason}'
    )
    
    return order


def update_order_status(order, user, new_status, comment=''):
    """
    Обновить статус заказа.
    """
    if new_status not in dict(Order.Status.choices):
        raise ValueError('Некорректный статус')
    
    old_status = order.status
    order.status = new_status
    order.save()
    
    # Создаем запись в истории
    description = f'Статус изменен с {order.get_status_display(old_status)} на {order.get_status_display(new_status)}'
    if comment:
        description += f'. Комментарий: {comment}'
    
    create_order_history(
        order=order,
        user=user,
        action='Изменен статус',
        field='status',
        old_value=old_status,
        new_value=new_status,
        description=description
    )
    
    return order


def create_order_history(order, user, action, field='', old_value='', new_value='', description=''):
    """
    Создать запись в истории заказа.
    """
    OrderHistory.objects.create(
        order=order,
        user=user,
        action=action,
        field=field,
        old_value=old_value,
        new_value=new_value,
        description=description
    )


def calculate_order_statistics(user, period='month', date_from=None, date_to=None):
    """
    Рассчитать статистику заказов.
    """
    # Определяем период
    end_date = timezone.now().date()
    
    if period == 'day':
        start_date = end_date - timedelta(days=1)
    elif period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'year':
        start_date = end_date - timedelta(days=365)
    elif period == 'custom' and date_from and date_to:
        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
    else:
        start_date = end_date - timedelta(days=30)
    
    # Фильтруем заказы пользователя
    if user.is_superuser or user.role == 'admin':
        orders = Order.objects.all()
    else:
        orders = Order.objects.filter(created_by=user)
    
    orders = orders.filter(
        created_at__date__range=[start_date, end_date]
    )
    
    # Рассчитываем статистику
    total_orders = orders.count()
    total_amount = orders.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    avg_order_value = orders.aggregate(
        avg=Avg('total_amount')
    )['avg'] or 0
    
    paid_amount = orders.aggregate(
        paid=Sum('paid_amount')
    )['paid'] or 0
    
    # По статусам
    by_status = orders.values('status').annotate(
        count=Count('id')
    )
    status_dict = {
        item['status']: item['count']
        for item in by_status
    }
    
    # По магазинам
    by_store = orders.values(
        'store__id',
        'store__name'
    ).annotate(
        count=Count('id'),
        amount=Sum('total_amount')
    ).order_by('-amount')
    
    store_list = [
        {
            'store_id': item['store__id'],
            'store_name': item['store__name'],
            'count': item['count'],
            'amount': float(item['amount'] or 0)
        }
        for item in by_store
    ]
    
    # По дням
    from django.db.models.functions import TruncDate
    by_day = orders.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id'),
        amount=Sum('total_amount')
    ).order_by('date')
    
    day_list = [
        {
            'date': item['date'].strftime('%Y-%m-%d'),
            'count': item['count'],
            'amount': float(item['amount'] or 0)
        }
        for item in by_day
    ]
    
    return {
        'total_orders': total_orders,
        'total_amount': float(total_amount),
        'avg_order_value': float(avg_order_value),
        'paid_amount': float(paid_amount),
        'by_status': status_dict,
        'by_store': store_list,
        'by_day': day_list,
        'period': period,
        'date_from': start_date,
        'date_to': end_date
    }


def check_order_approval_required(order):
    """
    Проверить, требуется ли подтверждение заказа.
    """
    from apps.networks.models import NetworkSettings
    
    try:
        settings = NetworkSettings.objects.get(network=order.store.network)
        if not settings.require_approval:
            return False
        
        # Проверяем порог подтверждения
        return order.total_amount >= settings.approval_threshold
    
    except NetworkSettings.DoesNotExist:
        # По умолчанию требуем подтверждение для всех заказов
        return True

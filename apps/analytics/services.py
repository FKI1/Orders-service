from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F, Q, Value
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.db import connection
from collections import defaultdict
import pandas as pd
from io import BytesIO

from apps.orders.models import Order, OrderItem
from apps.products.models import Product
from apps.users.models import User


def calculate_order_stats(queryset, start_date, end_date, period='month'):
    """
    Рассчитывает статистику заказов за период.
    """
    # Базовая статистика
    total_orders = queryset.count()
    total_amount = queryset.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    avg_order_amount = total_amount / total_orders if total_orders > 0 else 0
    
    # Статистика по статусам
    status_stats = queryset.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    by_status = {item['status']: item['count'] for item in status_stats}
    
    # Статистика по дням
    if period in ['day', 'custom']:
        trunc_func = TruncDate('created_at')
    elif period == 'week':
        trunc_func = TruncWeek('created_at')
    else:  # month, year
        trunc_func = TruncMonth('created_at')
    
    daily_stats = queryset.annotate(
        period=trunc_func
    ).values('period').annotate(
        count=Count('id'),
        amount=Sum('total_amount')
    ).order_by('period')
    
    by_day = [
        {
            'date': item['period'].strftime('%Y-%m-%d'),
            'count': item['count'],
            'amount': float(item['amount'] or 0)
        }
        for item in daily_stats
    ]
    
    # Топ товаров
    top_products = OrderItem.objects.filter(
        order__in=queryset
    ).values(
        'product__id',
        'product__name',
        'product__sku'
    ).annotate(
        quantity=Sum('quantity'),
        amount=Sum('total')
    ).order_by('-amount')[:10]
    
    top_products_list = [
        {
            'product_id': item['product__id'],
            'product_name': item['product__name'],
            'sku': item['product__sku'],
            'quantity': item['quantity'] or 0,
            'amount': float(item['amount'] or 0)
        }
        for item in top_products
    ]
    
    return {
        'total_orders': total_orders,
        'total_amount': float(total_amount),
        'avg_order_amount': float(avg_order_amount),
        'by_status': by_status,
        'by_day': by_day,
        'top_products': top_products_list,
        'period': period,
        'date_from': start_date.date(),
        'date_to': end_date.date()
    }


def get_budget_report(user):
    """
    Генерирует отчет по остаткам бюджета.
    """
    
    monthly_budget = 500000.00  # Пример бюджета
    
    # Рассчитываем потраченную сумму за текущий месяц
    today = timezone.now()
    first_day = today.replace(day=1)
    
    spent = Order.objects.filter(
        created_by=user,
        created_at__gte=first_day,
        status__in=['approved', 'processing', 'delivered']
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    remaining = monthly_budget - spent
    utilization_percentage = (spent / monthly_budget * 100) if monthly_budget > 0 else 0
    
    # По магазинам (пример)
    by_store = [
        {
            'store_id': 1,
            'store_name': 'Магазин №1',
            'budget': 100000,
            'spent': 75000,
            'remaining': 25000,
            'utilization': 75.0
        }
    ]
    
    # По категориям (пример)
    by_category = [
        {
            'category_id': 1,
            'category_name': 'Напитки',
            'spent': 30000,
            'percentage': 40.0
        }
    ]
    
    # Предупреждения
    warnings = []
    if utilization_percentage > 80:
        warnings.append('Бюджет использован более чем на 80%')
    if utilization_percentage > 95:
        warnings.append('Бюджет почти исчерпан!')
    
    return {
        'monthly_budget': float(monthly_budget),
        'spent': float(spent),
        'remaining': float(remaining),
        'utilization_percentage': float(utilization_percentage),
        'by_store': by_store,
        'by_category': by_category,
        'warnings': warnings
    }


def get_top_products(user, limit=10, period='month', category_id=None):
    """
    Возвращает топ товаров по продажам.
    """
    # Определяем период
    end_date = timezone.now()
    
    if period == 'day':
        start_date = end_date - timedelta(days=1)
    elif period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'year':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)
    
    # Базовый запрос
    order_items = OrderItem.objects.filter(
        order__created_at__range=[start_date, end_date],
        order__created_by=user
    )
    
    # Фильтр по категории
    if category_id:
        order_items = order_items.filter(
            product__category_id=category_id
        )
    
    # Агрегация
    top_items = order_items.values(
        'product__id',
        'product__name',
        'product__sku',
        'product__category__name'
    ).annotate(
        quantity=Sum('quantity'),
        amount=Sum('total')
    ).order_by('-amount')[:limit]
    
    # Общая сумма для расчета процентов
    total_amount = sum(item['amount'] or 0 for item in top_items)
    
    # Форматируем результат
    result = []
    for item in top_items:
        amount = item['amount'] or 0
        percentage = (amount / total_amount * 100) if total_amount > 0 else 0
        
        result.append({
            'product_id': item['product__id'],
            'product_name': item['product__name'],
            'sku': item['product__sku'],
            'category': item['product__category__name'],
            'quantity': item['quantity'] or 0,
            'amount': float(amount),
            'percentage': round(percentage, 2)
        })
    
    return result


def get_sales_trend(user, period='day', days=30):
    """
    Возвращает тренд продаж за период.
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Определяем функцию для группировки
    if period == 'day':
        trunc_func = TruncDate('created_at')
        date_format = '%Y-%m-%d'
    elif period == 'week':
        trunc_func = TruncWeek('created_at')
        date_format = 'W%U %Y'
    else:  # month
        trunc_func = TruncMonth('created_at')
        date_format = '%b %Y'
    
    # Получаем данные
    orders = Order.objects.filter(
        created_by=user,
        created_at__range=[start_date, end_date]
    )
    
    trend_data = orders.annotate(
        period_date=trunc_func
    ).values('period_date').annotate(
        orders_count=Count('id'),
        amount=Sum('total_amount')
    ).order_by('period_date')
    
    # Заполняем пропущенные периоды нулями
    result = []
    current_date = start_date
    
    while current_date <= end_date:
        period_str = current_date.strftime(date_format)
        
        # Ищем данные для этого периода
        data = next(
            (item for item in trend_data 
             if item['period_date'].strftime(date_format) == period_str),
            None
        )
        
        if data:
            avg_value = data['amount'] / data['orders_count'] if data['orders_count'] > 0 else 0
            result.append({
                'period': period_str,
                'date': data['period_date'].date(),
                'orders_count': data['orders_count'],
                'amount': float(data['amount'] or 0),
                'avg_order_value': float(avg_value)
            })
        else:
            result.append({
                'period': period_str,
                'date': current_date.date(),
                'orders_count': 0,
                'amount': 0,
                'avg_order_value': 0
            })
        
        # Переходим к следующему периоду
        if period == 'day':
            current_date += timedelta(days=1)
        elif period == 'week':
            current_date += timedelta(weeks=1)
        else:  # month
            # Переход к следующему месяцу
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
    
    return result


def get_supplier_analytics(user):
    """
    Аналитика по поставщикам.
    """
    # Получаем всех поставщиков, с которыми работал пользователь
    suppliers = User.objects.filter(
        role='supplier',
        products__order_items__order__created_by=user
    ).distinct()
    
    result = []
    
    for supplier in suppliers:
        # Заказы с товарами этого поставщика
        supplier_orders = Order.objects.filter(
            items__product__supplier=supplier,
            created_by=user
        ).distinct()
        
        total_orders = supplier_orders.count()
        total_amount = supplier_orders.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        avg_order_amount = total_amount / total_orders if total_orders > 0 else 0
        
        # Количество товаров поставщика
        product_count = supplier.products.count()
        
        # Самый популярный товар
        top_product = supplier.products.annotate(
            total_sold=Sum('order_items__quantity')
        ).order_by('-total_sold').first()
        
        # Рейтинг (пример)
        rating = 4.5  
        
        # Время доставки (пример)
        on_time_delivery = 92.5  
        
        # Дата последнего заказа
        last_order = supplier_orders.order_by('-created_at').first()
        last_order_date = last_order.created_at.date() if last_order else None
        
        # Уровень активности
        if total_orders > 20:
            activity_level = 'high'
        elif total_orders > 5:
            activity_level = 'medium'
        else:
            activity_level = 'low'
        
        result.append({
            'id': supplier.id,
            'get_full_name': supplier.get_full_name(),
            'company_name': supplier.company_name or 'Не указано',
            'total_orders': total_orders,
            'total_amount': float(total_amount),
            'avg_order_amount': float(avg_order_amount),
            'product_count': product_count,
            'top_product': top_product.name if top_product else 'Нет данных',
            'rating': rating,
            'on_time_delivery': on_time_delivery,
            'last_order_date': last_order_date,
            'activity_level': activity_level
        })
    
    return result


def generate_daily_report(user, date):
    """
    Генерирует ежедневный отчет.
    """
    date_obj = datetime.strptime(date, '%Y-%m-%d').date() if isinstance(date, str) else date
    
    orders_today = Order.objects.filter(
        created_by=user,
        created_at__date=date_obj
    )
    
    orders_count = orders_today.count()
    total_amount = orders_today.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Новые заказы
    new_orders = orders_today.filter(status='pending').count()
    
    # Завершенные заказы
    completed_orders = orders_today.filter(status='delivered').count()
    
    # Товары дня
    products_today = OrderItem.objects.filter(
        order__created_at__date=date_obj,
        order__created_by=user
    ).values(
        'product__name'
    ).annotate(
        quantity=Sum('quantity'),
        amount=Sum('total')
    ).order_by('-quantity')[:5]
    
    return {
        'date': date_obj.strftime('%Y-%m-%d'),
        'summary': {
            'orders_count': orders_count,
            'total_amount': float(total_amount),
            'new_orders': new_orders,
            'completed_orders': completed_orders,
            'avg_order_value': float(total_amount / orders_count) if orders_count > 0 else 0
        },
        'top_products': list(products_today),
        'orders_by_hour': _get_orders_by_hour(user, date_obj)
    }


def _get_orders_by_hour(user, date):
    """Вспомогательная функция: заказы по часам"""
    # Упрощенная реализация
    return [
        {'hour': f'{h}:00', 'count': 0}
        for h in range(24)
    ]


def export_to_excel(user, report_type='orders', date_from=None, date_to=None):
    """
    Экспорт данных в Excel.
    """
    # Создаем DataFrame с данными
    if report_type == 'orders':
        queryset = Order.objects.filter(created_by=user)
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        data = list(queryset.values(
            'order_number', 'status', 'total_amount', 
            'created_at', 'delivery_date'
        ))
        
        df = pd.DataFrame(data)
    
    elif report_type == 'products':
        order_items = OrderItem.objects.filter(
            order__created_by=user
        )
        
        if date_from:
            order_items = order_items.filter(order__created_at__date__gte=date_from)
        if date_to:
            order_items = order_items.filter(order__created_at__date__lte=date_to)
        
        data = list(order_items.values(
            'product__name', 'product__sku', 'quantity',
            'price', 'total', 'order__order_number'
        ))
        
        df = pd.DataFrame(data)
    
    else:  # suppliers
        suppliers_data = get_supplier_analytics(user)
        df = pd.DataFrame(suppliers_data)
    
    # Создаем Excel файл в памяти
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Report', index=False)
    
    output.seek(0)
    return output.getvalue()

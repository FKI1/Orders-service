from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum, F
from datetime import timedelta, datetime
from apps.users.models import User
from apps.products.models import Product
from apps.orders.models import Order, OrderItem


def get_supplier_statistics(supplier):
    """
    Получить статистику поставщика.
    """
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Общая статистика
    total_products = Product.objects.filter(supplier=supplier).count()
    
    # Заказы поставщика
    supplier_orders = Order.objects.filter(
        items__product__supplier=supplier
    ).distinct()
    
    total_orders = supplier_orders.count()
    total_revenue = supplier_orders.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Заказы по периодам
    today_orders = supplier_orders.filter(created_at__date=today).count()
    week_orders = supplier_orders.filter(created_at__date__gte=week_ago).count()
    month_orders = supplier_orders.filter(created_at__date__gte=month_ago).count()
    
    today_revenue = supplier_orders.filter(
        created_at__date=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    week_revenue = supplier_orders.filter(
        created_at__date__gte=week_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    month_revenue = supplier_orders.filter(
        created_at__date__gte=month_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Заказы по статусам
    orders_by_status = supplier_orders.values('status').annotate(
        count=Count('id')
    )
    
    status_dict = {
        item['status']: item['count']
        for item in orders_by_status
    }
    
    # Топ товары
    top_products = Product.objects.filter(
        supplier=supplier,
        order_items__isnull=False
    ).annotate(
        total_sold=Sum('order_items__quantity'),
        total_revenue=Sum('order_items__total')
    ).order_by('-total_revenue')[:5]
    
    top_products_list = []
    for product in top_products:
        top_products_list.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'total_sold': product.total_sold or 0,
            'total_revenue': float(product.total_revenue or 0)
        })
    
    
    avg_rating = 4.5  
    on_time_delivery_rate = 92.5  
    response_time_avg = 2.5  
    
    # Активность
    last_order = supplier_orders.order_by('-created_at').first()
    last_order_date = last_order.created_at.date() if last_order else None
    
    days_since_last_order = (
        (today - last_order_date).days 
        if last_order_date else None
    )
    
    # Уровень активности
    if month_orders > 20:
        activity_level = 'high'
    elif month_orders > 5:
        activity_level = 'medium'
    else:
        activity_level = 'low'
    
    return {
        'supplier_id': supplier.id,
        'supplier_name': f"{supplier.first_name} {supplier.last_name}",
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': float(total_revenue),
        'today_orders': today_orders,
        'week_orders': week_orders,
        'month_orders': month_orders,
        'today_revenue': float(today_revenue),
        'week_revenue': float(week_revenue),
        'month_revenue': float(month_revenue),
        'orders_by_status': status_dict,
        'top_products': top_products_list,
        'avg_rating': avg_rating,
        'on_time_delivery_rate': on_time_delivery_rate,
        'response_time_avg': response_time_avg,
        'last_order_date': last_order_date,
        'days_since_last_order': days_since_last_order,
        'activity_level': activity_level
    }


def calculate_supplier_rating(supplier):
    """
    Рассчитать рейтинг поставщика.
    В реальном проекте здесь будет сложная логика.
    """
  
    return 4.5


def get_supplier_orders_summary(supplier):
    """
    Сводка по заказам поставщика.
    """
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Все заказы поставщика
    all_orders = Order.objects.filter(
        items__product__supplier=supplier
    ).distinct()
    
    # Заказы по периодам
    orders_today = all_orders.filter(created_at__date=today)
    orders_week = all_orders.filter(created_at__date__gte=week_ago)
    orders_month = all_orders.filter(created_at__date__gte=month_ago)
    
    # Рассчитываем метрики
    summary = {
        'all_time': {
            'count': all_orders.count(),
            'amount': float(all_orders.aggregate(
                total=Sum('total_amount')
            )['total'] or 0),
            'avg_order_value': float(all_orders.aggregate(
                avg=Avg('total_amount')
            )['avg'] or 0)
        },
        'month': {
            'count': orders_month.count(),
            'amount': float(orders_month.aggregate(
                total=Sum('total_amount')
            )['total'] or 0),
            'avg_order_value': float(orders_month.aggregate(
                avg=Avg('total_amount')
            )['avg'] or 0)
        },
        'week': {
            'count': orders_week.count(),
            'amount': float(orders_week.aggregate(
                total=Sum('total_amount')
            )['total'] or 0),
            'avg_order_value': float(orders_week.aggregate(
                avg=Avg('total_amount')
            )['avg'] or 0)
        },
        'today': {
            'count': orders_today.count(),
            'amount': float(orders_today.aggregate(
                total=Sum('total_amount')
            )['total'] or 0),
            'avg_order_value': float(orders_today.aggregate(
                avg=Avg('total_amount')
            )['avg'] or 0)
        }
    }
    
    return summary


def generate_supplier_report(supplier, date_from=None, date_to=None):
    """
    Сгенерировать отчет по поставщику.
    """
    # Определяем период
    if not date_from:
        date_from = timezone.now().date() - timedelta(days=30)
    
    if not date_to:
        date_to = timezone.now().date()
    
    # Заказы за период
    orders = Order.objects.filter(
        items__product__supplier=supplier,
        created_at__date__range=[date_from, date_to]
    ).distinct()
    
    # Товары поставщика
    products = Product.objects.filter(supplier=supplier)
    
    # Собираем отчет
    report = {
        'supplier': {
            'id': supplier.id,
            'name': f"{supplier.first_name} {supplier.last_name}",
            'company': supplier.company_name,
            'email': supplier.email,
            'phone': supplier.phone
        },
        'period': {
            'from': date_from,
            'to': date_to
        },
        'orders_summary': {
            'total_orders': orders.count(),
            'total_amount': float(orders.aggregate(
                total=Sum('total_amount')
            )['total'] or 0),
            'avg_order_value': float(orders.aggregate(
                avg=Avg('total_amount')
            )['avg'] or 0),
            'by_status': {
                status: orders.filter(status=status).count()
                for status in ['pending', 'approved', 'processing', 'delivered', 'cancelled']
            }
        },
        'products_summary': {
            'total_products': products.count(),
            'in_stock': products.filter(in_stock=True).count(),
            'out_of_stock': products.filter(in_stock=False).count(),
            'by_category': list(products.values('category__name').annotate(
                count=Count('id')
            ))
        },
        'top_products': list(
            OrderItem.objects.filter(
                product__supplier=supplier,
                order__created_at__date__range=[date_from, date_to]
            ).values(
                'product__name',
                'product__sku'
            ).annotate(
                quantity=Sum('quantity'),
                revenue=Sum('total')
            ).order_by('-revenue')[:10]
        ),
        'generated_at': timezone.now().isoformat()
    }
    
    return report


def send_supplier_notification(supplier, notification_type, data):
    """
    Отправить уведомление поставщику.
    """
    # Здесь будет логика отправки email, SMS или push-уведомлений
    # Пока просто заглушка
    print(f"Отправка уведомления поставщику {supplier.email}: {notification_type}")
    print(f"Данные: {data}")
    
    return True

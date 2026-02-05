from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg, F
from datetime import timedelta, datetime
from .models import RetailNetwork, Store, StoreAssignment


def calculate_network_stats(network):
    """
    Рассчитать статистику сети.
    """
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    from apps.orders.models import Order
    
    # Все заказы сети
    network_orders = Order.objects.filter(store__network=network)
    
    # Основная статистика
    stores_count = network.stores.count()
    employees_count = network.employees.count()
    total_orders = network_orders.count()
    total_revenue = network_orders.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Бюджет
    monthly_budget = network.monthly_budget
    monthly_spent = network.monthly_spent
    budget_utilization = network.budget_utilization
    
    # Заказы по периодам
    today_orders = network_orders.filter(created_at__date=today).count()
    week_orders = network_orders.filter(created_at__date__gte=week_ago).count()
    month_orders = network_orders.filter(created_at__date__gte=month_ago).count()
    
    today_revenue = network_orders.filter(
        created_at__date=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    week_revenue = network_orders.filter(
        created_at__date__gte=week_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    month_revenue = network_orders.filter(
        created_at__date__gte=month_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Заказы по статусам
    orders_by_status = network_orders.values('status').annotate(
        count=Count('id')
    )
    status_dict = {
        item['status']: item['count']
        for item in orders_by_status
    }
    
    # Магазины по городам
    stores_by_city = network.stores.values('city').annotate(
        count=Count('id'),
        total_orders=Count('orders')
    ).order_by('-count')
    
    # Топ магазинов по выручке за месяц
    top_stores = network.stores.annotate(
        month_revenue=Sum(
            'orders__total_amount',
            filter=Q(orders__created_at__date__gte=month_ago)
        )
    ).order_by('-month_revenue')[:5]
    
    top_stores_list = []
    for store in top_stores:
        top_stores_list.append({
            'id': store.id,
            'name': store.name,
            'city': store.city,
            'month_revenue': store.month_revenue or 0,
            'total_orders': store.total_orders
        })
    
    return {
        'network_id': network.id,
        'network_name': network.name,
        'stores_count': stores_count,
        'employees_count': employees_count,
        'total_orders': total_orders,
        'total_revenue': float(total_revenue),
        'monthly_budget': float(monthly_budget),
        'monthly_spent': float(monthly_spent),
        'budget_utilization': budget_utilization,
        'today_orders': today_orders,
        'week_orders': week_orders,
        'month_orders': month_orders,
        'today_revenue': float(today_revenue),
        'week_revenue': float(week_revenue),
        'month_revenue': float(month_revenue),
        'orders_by_status': status_dict,
        'stores_by_city': list(stores_by_city),
        'top_stores': top_stores_list
    }


def calculate_store_stats(store):
    """
    Рассчитать статистику магазина.
    """
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    from apps.orders.models import Order
    from apps.orders.models import OrderItem
    
    # Все заказы магазина
    store_orders = Order.objects.filter(store=store)
    
    # Основная статистика
    total_orders = store_orders.count()
    total_revenue = store_orders.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    avg_order_value = store_orders.aggregate(
        avg=Avg('total_amount')
    )['avg'] or 0
    
    # Бюджет
    monthly_budget = store.monthly_budget
    monthly_spent = store.monthly_spent
    budget_utilization = store.budget_utilization
    
    # Заказы по периодам
    today_orders = store_orders.filter(created_at__date=today).count()
    week_orders = store_orders.filter(created_at__date__gte=week_ago).count()
    month_orders = store_orders.filter(created_at__date__gte=month_ago).count()
    
    today_revenue = store_orders.filter(
        created_at__date=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    week_revenue = store_orders.filter(
        created_at__date__gte=week_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    month_revenue = store_orders.filter(
        created_at__date__gte=month_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Заказы по статусам
    orders_by_status = store_orders.values('status').annotate(
        count=Count('id')
    )
    status_dict = {
        item['status']: item['count']
        for item in orders_by_status
    }
    
    # Топ товаров
    top_products = OrderItem.objects.filter(
        order__store=store,
        order__created_at__date__gte=month_ago
    ).values(
        'product__name',
        'product__sku'
    ).annotate(
        quantity=Sum('quantity'),
        revenue=Sum('total')
    ).order_by('-revenue')[:5]
    
    top_products_list = [
        {
            'name': item['product__name'],
            'sku': item['product__sku'],
            'quantity': item['quantity'] or 0,
            'revenue': float(item['revenue'] or 0)
        }
        for item in top_products
    ]
    
    # Активность
    last_order = store_orders.order_by('-created_at').first()
    last_order_date = last_order.created_at.date() if last_order else None
    
    days_since_last_order = (
        (today - last_order_date).days 
        if last_order_date else None
    )
    
    return {
        'store_id': store.id,
        'store_name': store.name,
        'network_name': store.network.name,
        'total_orders': total_orders,
        'total_revenue': float(total_revenue),
        'avg_order_value': float(avg_order_value),
        'monthly_budget': float(monthly_budget),
        'monthly_spent': float(monthly_spent),
        'budget_utilization': budget_utilization,
        'today_orders': today_orders,
        'week_orders': week_orders,
        'month_orders': month_orders,
        'today_revenue': float(today_revenue),
        'week_revenue': float(week_revenue),
        'month_revenue': float(month_revenue),
        'orders_by_status': status_dict,
        'top_products': top_products_list,
        'last_order_date': last_order_date,
        'days_since_last_order': days_since_last_order
    }


def get_network_dashboard(network):
    """
    Получить данные для дашборда сети.
    """
    stats = calculate_network_stats(network)
    
    # Дополнительные данные для дашборда
    today = timezone.now().date()
    from apps.orders.models import Order
    
    # Последние заказы
    recent_orders = Order.objects.filter(
        store__network=network
    ).order_by('-created_at')[:10].values(
        'id', 'order_number', 'store__name', 'total_amount', 'status', 'created_at'
    )
    
    # Магазины с низким бюджетом
    low_budget_stores = network.stores.filter(
        monthly_budget__gt=0
    ).annotate(
        utilization=(F('monthly_spent') / F('monthly_budget') * 100)
    ).filter(utilization__gte=80).values(
        'id', 'name', 'monthly_budget', 'monthly_spent'
    )
    
    # Сводка по сотрудникам
    from apps.users.models import User
    employees_by_role = network.employees.values('role').annotate(
        count=Count('id')
    )
    
    return {
        'stats': stats,
        'recent_orders': list(recent_orders),
        'low_budget_stores': list(low_budget_stores),
        'employees_by_role': list(employees_by_role),
        'timestamp': timezone.now().isoformat()
    }


def get_store_dashboard(store):
    """
    Получить данные для дашборда магазина.
    """
    stats = calculate_store_stats(store)
    
    # Дополнительные данные для дашборда
    today = timezone.now().date()
    from apps.orders.models import Order
    
    # Последние заказы
    recent_orders = Order.objects.filter(
        store=store
    ).order_by('-created_at')[:10].values(
        'id', 'order_number', 'total_amount', 'status', 'created_at'
    )
    
    # Товары с низким остатком (если есть связь с инвентарем)
    low_stock_products = []
    # Здесь можно добавить логику получения товаров с низким остатком
    
    # Бюджетная информация
    budget_warning = None
    if store.budget_utilization >= 80:
        budget_warning = {
            'level': 'warning' if store.budget_utilization < 95 else 'critical',
            'message': f'Бюджет использован на {store.budget_utilization:.1f}%',
            'utilization': store.budget_utilization
        }
    
    return {
        'stats': stats,
        'recent_orders': list(recent_orders),
        'low_stock_products': low_stock_products,
        'budget_warning': budget_warning,
        'timestamp': timezone.now().isoformat()
    }


def assign_user_to_store(user, store, role, is_primary=False, assigned_by=None):
    """
    Назначить пользователя на магазин.
    """
    # Если пользователь уже назначен на этот магазин, обновляем назначение
    assignment, created = StoreAssignment.objects.update_or_create(
        user=user,
        store=store,
        defaults={
            'role': role,
            'is_primary': is_primary,
            'assigned_by': assigned_by
        }
    )
    
    # Если это основное место работы, снимаем флаг у других назначений
    if is_primary:
        StoreAssignment.objects.filter(
            user=user,
            is_primary=True
        ).exclude(id=assignment.id).update(is_primary=False)
    
    # Обновляем количество сотрудников в магазине
    store.staff_count = store.assignments.count()
    if store.manager is None and user.role == 'store_manager':
        store.manager = user
    store.save()
    
    return assignment


def remove_user_from_store(user, store):
    """
    Удалить пользователя из магазина.
    """
    try:
        assignment = StoreAssignment.objects.get(user=user, store=store)
        assignment.delete()
        
        # Обновляем количество сотрудников
        store.staff_count = store.assignments.count()
        
        # Если удаляемый пользователь был менеджером, сбрасываем менеджера
        if store.manager == user:
            store.manager = None
        
        store.save()
        return True
    
    except StoreAssignment.DoesNotExist:
        return False


def update_network_budget(network, new_budget):
    """
    Обновить бюджет сети.
    """
    network.monthly_budget = new_budget
    network.save()
    return network


def update_store_budget(store, new_budget):
    """
    Обновить бюджет магазина.
    """
    store.monthly_budget = new_budget
    store.save()
    return store


def get_network_by_tax_id(tax_id):
    """
    Получить сеть по ИНН.
    """
    try:
        return RetailNetwork.objects.get(tax_id=tax_id)
    except RetailNetwork.DoesNotExist:
        return None


def get_store_by_code(network, store_code):
    """
    Получить магазин по коду в рамках сети.
    """
    try:
        return Store.objects.get(network=network, store_code=store_code)
    except Store.DoesNotExist:
        return None


def search_stores(query, network=None):
    """
    Поиск магазинов.
    """
    stores = Store.objects.all()
    
    if network:
        stores = stores.filter(network=network)
    
    if query:
        stores = stores.filter(
            Q(name__icontains=query) |
            Q(store_code__icontains=query) |
            Q(address__icontains=query) |
            Q(city__icontains=query)
        )
    
    return stores


def get_active_stores(network=None):
    """
    Получить активные магазины.
    """
    stores = Store.objects.filter(status='active')
    
    if network:
        stores = stores.filter(network=network)
    
    return stores

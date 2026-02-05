from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg, F
from datetime import timedelta
import csv
from io import StringIO
from .models import Product, Category


def search_products(user, query='', category_id=None, supplier_id=None, 
                   min_price=None, max_price=None, in_stock=None):
    """
    Поиск товаров.
    """
    # Базовый queryset в зависимости от прав пользователя
    if user.is_superuser or user.role == 'admin':
        products = Product.objects.all()
    elif user.role == 'supplier':
        products = Product.objects.filter(supplier=user)
    else:
        products = Product.objects.filter(
            status=Product.ProductStatus.ACTIVE,
            in_stock=True
        )
    
    # Применяем фильтры
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(short_description__icontains=query) |
            Q(description__icontains=query)
        )
    
    if category_id:
        try:
            category = Category.objects.get(id=category_id)
            # Ищем товары в этой категории и всех подкатегориях
            subcategories = category.get_all_subcategories()
            subcategories.append(category)
            products = products.filter(category__in=subcategories)
        except Category.DoesNotExist:
            pass
    
    if supplier_id:
        products = products.filter(supplier_id=supplier_id)
    
    if min_price:
        products = products.filter(price__gte=float(min_price))
    
    if max_price:
        products = products.filter(price__lte=float(max_price))
    
    if in_stock and in_stock.lower() == 'true':
        products = products.filter(in_stock=True)
    
    return products.order_by('-created_at')


def get_products_by_category(category, user):
    """
    Получить товары категории.
    """
    # Получаем все подкатегории
    subcategories = category.get_all_subcategories()
    subcategories.append(category)
    
    # Базовый queryset в зависимости от прав пользователя
    if user.is_superuser or user.role == 'admin':
        return Product.objects.filter(category__in=subcategories)
    elif user.role == 'supplier':
        return Product.objects.filter(
            category__in=subcategories,
            supplier=user
        )
    else:
        return Product.objects.filter(
            category__in=subcategories,
            status=Product.ProductStatus.ACTIVE,
            in_stock=True
        )


def get_popular_products(user, limit=10, category_id=None):
    """
    Получить популярные товары.
    """
    # Базовый queryset в зависимости от прав пользователя
    if user.is_superuser or user.role == 'admin':
        products = Product.objects.all()
    elif user.role == 'supplier':
        products = Product.objects.filter(supplier=user)
    else:
        products = Product.objects.filter(
            status=Product.ProductStatus.ACTIVE,
            in_stock=True
        )
    
    # Фильтр по категории
    if category_id:
        try:
            category = Category.objects.get(id=category_id)
            subcategories = category.get_all_subcategories()
            subcategories.append(category)
            products = products.filter(category__in=subcategories)
        except Category.DoesNotExist:
            pass
    
    # Сортируем по популярности (количество заказов)
    return products.order_by('-total_ordered', '-rating')[:limit]


def get_recommended_products(user, limit=10, category_id=None):
    """
    Получить рекомендованные товары.
    """
    # Базовый queryset в зависимости от прав пользователя
    if user.is_superuser or user.role == 'admin':
        products = Product.objects.all()
    elif user.role == 'supplier':
        products = Product.objects.filter(supplier=user)
    else:
        products = Product.objects.filter(
            status=Product.ProductStatus.ACTIVE,
            in_stock=True
        )
    
    # Фильтр по категории
    if category_id:
        try:
            category = Category.objects.get(id=category_id)
            subcategories = category.get_all_subcategories()
            subcategories.append(category)
            products = products.filter(category__in=subcategories)
        except Category.DoesNotExist:
            pass
    
    # Сортируем по рейтингу и новизне
    return products.order_by('-rating', '-created_at')[:limit]


def update_product_stock(product, quantity):
    """
    Обновить количество товара на складе.
    """
    product.update_stock(quantity)
    return product


def calculate_product_statistics(product):
    """
    Рассчитать статистику товара.
    """
    from apps.orders.models import OrderItem
    
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Получаем все заказы с этим товаром
    order_items = OrderItem.objects.filter(product=product)
    
    # Общая статистика
    total_ordered = order_items.aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    total_revenue = order_items.aggregate(
        total=Sum('total')
    )['total'] or 0
    
    avg_order_quantity = order_items.aggregate(
        avg=Avg('quantity')
    )['avg'] or 0
    
    # Статистика по периодам
    today_items = order_items.filter(
        created_at__date=today
    )
    today_ordered = today_items.aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    week_items = order_items.filter(
        created_at__date__gte=week_ago
    )
    week_ordered = week_items.aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    month_items = order_items.filter(
        created_at__date__gte=month_ago
    )
    month_ordered = month_items.aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    # Дата последнего заказа
    last_order_item = order_items.order_by('-created_at').first()
    last_ordered = last_order_item.created_at if last_order_item else None
    
    return {
        'product_id': product.id,
        'product_name': product.name,
        'sku': product.sku,
        'total_ordered': total_ordered,
        'total_revenue': float(total_revenue),
        'avg_order_quantity': float(avg_order_quantity),
        'stock_quantity': product.stock_quantity,
        'reserved_quantity': product.reserved_quantity,
        'available_quantity': product.available_quantity,
        'is_low_stock': product.is_low_stock,
        'price': float(product.price),
        'old_price': float(product.old_price) if product.old_price else None,
        'cost_price': float(product.cost_price) if product.cost_price else None,
        'margin': product.margin,
        'rating': float(product.rating),
        'total_reviews': product.total_reviews,
        'created_at': product.created_at,
        'updated_at': product.updated_at,
        'last_ordered': last_ordered,
        'today_ordered': today_ordered,
        'week_ordered': week_ordered,
        'month_ordered': month_ordered
    }


def export_products_to_csv(supplier_id=None):
    """
    Экспортировать товары в CSV.
    """
    # Получаем товары
    if supplier_id:
        products = Product.objects.filter(supplier_id=supplier_id)
    else:
        products = Product.objects.all()
    
    # Создаем CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    headers = [
        'ID', 'Артикул', 'Название', 'Категория', 'Поставщик',
        'Цена', 'Старая цена', 'Себестоимость', 'Единица',
        'Количество на складе', 'Зарезервировано', 'Доступно',
        'Минимальный заказ', 'Статус', 'В наличии', 'Рейтинг',
        'Количество отзывов', 'Всего заказано', 'Дата создания'
    ]
    
    writer.writerow(headers)
    
    # Данные
    for product in products:
        row = [
            product.id,
            product.sku,
            product.name,
            product.category.name if product.category else '',
            product.supplier.get_full_name() if product.supplier else '',
            str(product.price),
            str(product.old_price) if product.old_price else '',
            str(product.cost_price) if product.cost_price else '',
            product.unit,
            product.stock_quantity,
            product.reserved_quantity,
            product.available_quantity,
            product.min_order_quantity,
            product.get_status_display(),
            'Да' if product.in_stock else 'Нет',
            str(product.rating),
            product.total_reviews,
            product.total_ordered,
            product.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ]
        writer.writerow(row)
    
    return output.getvalue()


def update_product_rating(product):
    """
    Обновить рейтинг товара.
    """
    from .models import ProductReview
    
    reviews = product.reviews.filter(is_approved=True)
    if reviews.exists():
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        product.rating = round(avg_rating, 2)
        product.total_reviews = reviews.count()
        product.save()
    
    return product


def check_low_stock_products(user):
    """
    Проверить товары с низким остатком.
    """
    if user.is_superuser or user.role == 'admin':
        products = Product.objects.all()
    elif user.role == 'supplier':
        products = Product.objects.filter(supplier=user)
    else:
        return []
    
    low_stock_products = products.filter(
        stock_quantity__lte=F('min_stock_level'),
        in_stock=True
    ).order_by('stock_quantity')
    
    return low_stock_products

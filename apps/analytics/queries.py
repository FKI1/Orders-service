"""
Сложные SQL запросы для аналитики.
Оптимизированные запросы для больших объемов данных.
"""
from django.db import connection
from django.db.models import Q


def get_complex_sales_report(date_from, date_to, user_id=None):
    """
    Сложный отчет по продажам с множественными агрегациями.
    """
    query = """
    SELECT 
        DATE(o.created_at) as order_date,
        s.name as store_name,
        c.name as category_name,
        p.name as product_name,
        COUNT(DISTINCT o.id) as order_count,
        SUM(oi.quantity) as total_quantity,
        SUM(oi.total) as total_amount,
        AVG(oi.total / oi.quantity) as avg_price
    FROM orders_order o
    JOIN orders_orderitem oi ON o.id = oi.order_id
    JOIN products_product p ON oi.product_id = p.id
    JOIN products_category c ON p.category_id = c.id
    LEFT JOIN stores_store s ON o.store_id = s.id
    WHERE o.created_at BETWEEN %s AND %s
    """
    
    params = [date_from, date_to]
    
    if user_id:
        query += " AND o.created_by_id = %s"
        params.append(user_id)
    
    query += """
    GROUP BY 
        DATE(o.created_at),
        s.name,
        c.name,
        p.name
    ORDER BY 
        order_date DESC,
        total_amount DESC
    """
    
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        results = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]
    
    return results


def get_supplier_performance_raw(supplier_id=None):
    """
    Производительность поставщиков через raw SQL.
    """
    query = """
    SELECT 
        u.id as supplier_id,
        u.email as supplier_email,
        u.company_name,
        COUNT(DISTINCT o.id) as total_orders,
        SUM(o.total_amount) as total_revenue,
        AVG(o.total_amount) as avg_order_value,
        COUNT(DISTINCT p.id) as unique_products,
        MIN(o.created_at) as first_order_date,
        MAX(o.created_at) as last_order_date,
        AVG(DATEDIFF(o.delivery_date, o.created_at)) as avg_delivery_days
    FROM users_user u
    JOIN products_product p ON u.id = p.supplier_id
    JOIN orders_orderitem oi ON p.id = oi.product_id
    JOIN orders_order o ON oi.order_id = o.id
    WHERE u.role = 'supplier'
    """
    
    params = []
    
    if supplier_id:
        query += " AND u.id = %s"
        params.append(supplier_id)
    
    query += """
    GROUP BY u.id, u.email, u.company_name
    HAVING total_orders > 0
    ORDER BY total_revenue DESC
    """
    
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        results = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]
    
    return results


def get_daily_metrics(date):
    """
    Ежедневные метрики для дашборда.
    """
    query = """
    WITH daily_stats AS (
        SELECT 
            DATE(created_at) as stat_date,
            COUNT(*) as order_count,
            SUM(total_amount) as total_revenue,
            AVG(total_amount) as avg_order_value
        FROM orders_order
        WHERE DATE(created_at) = %s
        GROUP BY DATE(created_at)
    ),
    status_stats AS (
        SELECT 
            status,
            COUNT(*) as count
        FROM orders_order
        WHERE DATE(created_at) = %s
        GROUP BY status
    )
    SELECT 
        ds.*,
        ss.status,
        ss.count as status_count
    FROM daily_stats ds
    CROSS JOIN status_stats ss
    """
    
    with connection.cursor() as cursor:
        cursor.execute(query, [date, date])
        results = cursor.fetchall()
    
    return results

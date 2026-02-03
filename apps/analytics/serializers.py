from rest_framework import serializers
from django.db.models import Sum, Count, Avg
from apps.orders.models import Order
from apps.products.models import Product
from apps.users.models import User


class OrderStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики заказов"""
    
    total_orders = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    by_status = serializers.DictField(
        child=serializers.IntegerField()
    )
    
    by_day = serializers.ListField(
        child=serializers.DictField()
    )
    
    top_products = serializers.ListField(
        child=serializers.DictField()
    )
    
    period = serializers.CharField()
    date_from = serializers.DateField()
    date_to = serializers.DateField()


class BudgetReportSerializer(serializers.Serializer):
    """Сериализатор для отчета по бюджету"""
    
    monthly_budget = serializers.DecimalField(max_digits=12, decimal_places=2)
    spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    remaining = serializers.DecimalField(max_digits=12, decimal_places=2)
    utilization_percentage = serializers.FloatField()
    
    by_store = serializers.ListField(
        child=serializers.DictField()
    )
    
    by_category = serializers.ListField(
        child=serializers.DictField()
    )
    
    warnings = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


class TopProductSerializer(serializers.Serializer):
    """Сериализатор для топа товаров"""
    
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    sku = serializers.CharField()
    category = serializers.CharField()
    quantity = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    percentage = serializers.FloatField()


class TopProductsSerializer(serializers.ListSerializer):
    """Список топ товаров"""
    child = TopProductSerializer()


class SalesTrendItemSerializer(serializers.Serializer):
    """Элемент тренда продаж"""
    
    period = serializers.CharField()
    date = serializers.DateField()
    orders_count = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)


class SalesTrendSerializer(serializers.ListSerializer):
    """Список трендов продаж"""
    child = SalesTrendItemSerializer()


class SupplierAnalyticsSerializer(serializers.Serializer):
    """Аналитика по поставщикам"""
    
    supplier_id = serializers.IntegerField(source='id')
    supplier_name = serializers.CharField(source='get_full_name')
    company_name = serializers.CharField()
    
    total_orders = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    product_count = serializers.IntegerField()
    top_product = serializers.CharField()
    
    rating = serializers.FloatField()
    on_time_delivery = serializers.FloatField()
    
    last_order_date = serializers.DateField()
    activity_level = serializers.CharField()  # high/medium/low


class CustomReportSerializer(serializers.Serializer):
    """Сериализатор для кастомных отчетов"""
    
    metrics = serializers.ListField(
        child=serializers.CharField()
    )
    
    dimensions = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    
    filters = serializers.DictField(
        required=False
    )
    
    group_by = serializers.CharField(
        required=False,
        default='day'
    )


class ExportRequestSerializer(serializers.Serializer):
    """Сериализатор для запроса экспорта"""
    
    report_type = serializers.ChoiceField(
        choices=['orders', 'products', 'suppliers', 'custom']
    )
    
    format = serializers.ChoiceField(
        choices=['excel', 'pdf', 'csv'],
        default='excel'
    )
    
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    
    filters = serializers.DictField(required=False)

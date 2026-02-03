from rest_framework import serializers
from django.db.models import Avg, Count, Sum
from apps.users.models import User
from apps.products.models import Product
from apps.orders.models import Order, OrderItem


class SupplierSerializer(serializers.ModelSerializer):
    """
    Сериализатор для поставщиков (административный).
    """
    product_count = serializers.SerializerMethodField()
    total_orders = serializers.SerializerMethodField()
    total_revenue = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    last_order_date = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'company_name',
            'phone',
            'is_active',
            'date_joined',
            'last_login',
            'product_count',
            'total_orders',
            'total_revenue',
            'avg_rating',
            'last_order_date'
        ]
        read_only_fields = [
            'id', 'date_joined', 'last_login', 
            'product_count', 'total_orders', 'total_revenue',
            'avg_rating', 'last_order_date'
        ]
    
    def get_product_count(self, obj):
        """Количество товаров поставщика"""
        return Product.objects.filter(supplier=obj).count()
    
    def get_total_orders(self, obj):
        """Общее количество заказов"""
        return Order.objects.filter(
            items__product__supplier=obj
        ).distinct().count()
    
    def get_total_revenue(self, obj):
        """Общая выручка"""
        total = Order.objects.filter(
            items__product__supplier=obj
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        return float(total)
    
    def get_avg_rating(self, obj):
        """Средний рейтинг поставщика"""
        
        return 4.5  
    
    def get_last_order_date(self, obj):
        """Дата последнего заказа"""
        last_order = Order.objects.filter(
            items__product__supplier=obj
        ).order_by('-created_at').first()
        
        return last_order.created_at.date() if last_order else None


class SupplierProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для профиля поставщика (для самого поставщика).
    """
    statistics = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'company_name',
            'phone',
            'date_joined',
            'last_login',
            'statistics'
        ]
        read_only_fields = ['id', 'email', 'date_joined', 'last_login']
    
    def get_statistics(self, obj):
        """Статистика поставщика"""
        from .services import get_supplier_statistics
        return get_supplier_statistics(obj)


class SupplierOrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор для заказов поставщика.
    """
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    store_name = serializers.CharField(source='order.store.name', read_only=True)
    buyer_name = serializers.SerializerMethodField()
    total_amount = serializers.DecimalField(
        source='order.total_amount',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    created_at = serializers.DateTimeField(source='order.created_at', read_only=True)
    delivery_date = serializers.DateField(source='order.delivery_date', read_only=True)
    items_count = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'order_number',
            'store_name',
            'buyer_name',
            'status',
            'total_amount',
            'created_at',
            'delivery_date',
            'items_count',
            'items'
        ]
    
    def get_buyer_name(self, obj):
        """Имя покупателя"""
        buyer = obj.order.created_by
        return f"{buyer.first_name} {buyer.last_name}" if buyer else "Неизвестно"
    
    def get_items_count(self, obj):
        """Количество позиций в заказе от этого поставщика"""
        return OrderItem.objects.filter(
            order=obj.order,
            product__supplier=obj.product.supplier
        ).count()
    
    def get_items(self, obj):
        """Товары в заказе от этого поставщика"""
        items = OrderItem.objects.filter(
            order=obj.order,
            product__supplier=obj.product.supplier
        ).select_related('product')
        
        return [
            {
                'product_name': item.product.name,
                'sku': item.product.sku,
                'quantity': item.quantity,
                'price': float(item.price),
                'total': float(item.total)
            }
            for item in items
        ]


class SupplierProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для товаров поставщика.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    total_sold = serializers.SerializerMethodField()
    total_revenue = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id',
            'sku',
            'name',
            'description',
            'category',
            'category_name',
            'price',
            'unit',
            'min_order_quantity',
            'in_stock',
            'stock_quantity',
            'created_at',
            'updated_at',
            'total_sold',
            'total_revenue'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_sold(self, obj):
        """Общее количество проданных единиц"""
        total = OrderItem.objects.filter(product=obj).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        return total
    
    def get_total_revenue(self, obj):
        """Общая выручка от товара"""
        total = OrderItem.objects.filter(product=obj).aggregate(
            total=Sum('total')
        )['total'] or 0
        return float(total)
    
    def validate_price(self, value):
        """Валидация цены"""
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть положительной")
        return value
    
    def validate_min_order_quantity(self, value):
        """Валидация минимального количества заказа"""
        if value <= 0:
            raise serializers.ValidationError("Минимальное количество должно быть положительным")
        return value


class SupplierPerformanceSerializer(serializers.Serializer):
    """
    Сериализатор для производительности поставщика.
    """
    supplier_id = serializers.IntegerField()
    supplier_name = serializers.CharField()
    
    # Общая статистика
    total_products = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    # Временные периоды
    today_orders = serializers.IntegerField()
    week_orders = serializers.IntegerField()
    month_orders = serializers.IntegerField()
    
    today_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    week_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    month_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Статистика по статусам
    orders_by_status = serializers.DictField(child=serializers.IntegerField())
    
    # Топ товары
    top_products = serializers.ListField(
        child=serializers.DictField()
    )
    
    # Рейтинг и метрики
    avg_rating = serializers.FloatField()
    on_time_delivery_rate = serializers.FloatField()
    response_time_avg = serializers.FloatField()
    
    # Активность
    last_order_date = serializers.DateField()
    days_since_last_order = serializers.IntegerField()
    activity_level = serializers.CharField()


class CreateSupplierSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания поставщика.
    """
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = [
            'email',
            'first_name',
            'last_name',
            'company_name',
            'phone',
            'password',
            'confirm_password'
        ]
    
    def validate(self, data):
        """Проверка пароля"""
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Пароли не совпадают'
            })
        
        # Проверяем уникальность email
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({
                'email': 'Пользователь с таким email уже существует'
            })
        
        return data
    
    def create(self, validated_data):
        """Создание поставщика"""
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        user = User.objects.create(
            **validated_data,
            role='supplier',
            username=validated_data['email']  # Используем email как username
        )
        
        user.set_password(password)
        user.save()
        
        return user


class UpdateSupplierSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления поставщика.
    """
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'company_name',
            'phone',
            'is_active'
        ]
    
    def update(self, instance, validated_data):
        """Обновление поставщика"""
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.company_name = validated_data.get('company_name', instance.company_name)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        
        instance.save()
        return instance

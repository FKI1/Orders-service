from rest_framework import serializers
from django.db.models import Sum
from django.utils import timezone

from .models import Order, OrderItem, OrderHistory, Payment
from apps.networks.serializers import StoreSerializer
from apps.products.serializers import ProductShortSerializer
from apps.users.serializers import UserShortSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Сериализатор для позиции заказа.
    """
    product = ProductShortSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    sku = serializers.CharField(source='product.sku', read_only=True)
    unit = serializers.CharField(source='product.unit', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'order',
            'product_id',
            'product',
            'product_name',
            'sku',
            'unit',
            'quantity',
            'unit_price',
            'total',
            'created_at'
        ]
        read_only_fields = ['id', 'unit_price', 'total', 'created_at']
    
    def validate_quantity(self, value):
        """Валидация количества"""
        if value <= 0:
            raise serializers.ValidationError('Количество должно быть положительным')
        return value
    
    def validate(self, data):
        """Общая валидация"""
        product = data.get('product_id')
        if product:
            # Проверяем, что товар существует и доступен
            from apps.products.models import Product
            try:
                product_obj = Product.objects.get(id=product)
                if not product_obj.in_stock:
                    raise serializers.ValidationError({
                        'product_id': 'Товар временно отсутствует'
                    })
            except Product.DoesNotExist:
                raise serializers.ValidationError({
                    'product_id': 'Товар не найден'
                })
        
        return data


class OrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор для заказа.
    """
    order_number = serializers.CharField(read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'store',
            'store_name',
            'created_by',
            'created_by_name',
            'approved_by',
            'approved_by_name',
            'status',
            'status_display',
            'payment_status',
            'subtotal',
            'discount_amount',
            'total_amount',
            'paid_amount',
            'remaining_amount',
            'items_count',
            'total_quantity',
            'created_at',
            'updated_at',
            'required_delivery_date',
            'estimated_delivery_date'
        ]
        read_only_fields = [
            'id', 'order_number', 'created_at', 'updated_at',
            'subtotal', 'total_amount', 'paid_amount', 'remaining_amount',
            'items_count', 'total_quantity'
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детальной информации о заказе.
    """
    store = StoreSerializer(read_only=True)
    created_by = UserShortSerializer(read_only=True)
    approved_by = UserShortSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'store',
            'created_by',
            'approved_by',
            'status',
            'status_display',
            'payment_status',
            'payment_status_display',
            'subtotal',
            'discount_amount',
            'total_amount',
            'paid_amount',
            'remaining_amount',
            'items',
            'items_count',
            'total_quantity',
            'notes',
            'cancellation_reason',
            'rejection_reason',
            'created_at',
            'updated_at',
            'approved_at',
            'shipped_at',
            'delivered_at',
            'cancelled_at',
            'required_delivery_date',
            'estimated_delivery_date'
        ]
        read_only_fields = '__all__'


class CreateOrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания заказа.
    """
    items = OrderItemSerializer(many=True, required=False)
    store_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Order
        fields = [
            'store_id',
            'required_delivery_date',
            'estimated_delivery_date',
            'notes',
            'items'
        ]
    
    def validate(self, data):
        """Валидация данных заказа"""
        # Проверяем дату доставки
        delivery_date = data.get('required_delivery_date')
        if delivery_date and delivery_date < timezone.now().date():
            raise serializers.ValidationError({
                'required_delivery_date': 'Дата доставки не может быть в прошлом'
            })
        
        return data
    
    def create(self, validated_data):
        """Создание заказа с товарами"""
        items_data = validated_data.pop('items', [])
        store_id = validated_data.pop('store_id')
        
        # Получаем магазин
        from apps.networks.models import Store
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            raise serializers.ValidationError({
                'store_id': 'Магазин не найден'
            })
        
        # Создаем заказ
        order = Order.objects.create(
            store=store,
            created_by=self.context['request'].user,
            **validated_data
        )
        
        # Добавляем товары
        total_amount = 0
        for item_data in items_data:
            product_id = item_data.get('product_id')
            quantity = item_data.get('quantity')
            
            # Получаем товар
            from apps.products.models import Product
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                order.delete()
                raise serializers.ValidationError({
                    'items': f'Товар с ID {product_id} не найден'
                })
            
            # Создаем позицию заказа
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=product.price,
                total=product.price * quantity
            )
            
            total_amount += product.price * quantity
        
        # Обновляем суммы заказа
        order.subtotal = total_amount
        order.total_amount = total_amount - order.discount_amount
        order.save()
        
        return order


class UpdateOrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления заказа.
    """
    class Meta:
        model = Order
        fields = [
            'required_delivery_date',
            'estimated_delivery_date',
            'notes',
            'discount_amount'
        ]
    
    def validate_discount_amount(self, value):
        """Валидация суммы скидки"""
        if value < 0:
            raise serializers.ValidationError('Сумма скидки не может быть отрицательной')
        return value


class OrderStatusSerializer(serializers.Serializer):
    """
    Сериализатор для изменения статуса заказа.
    """
    status = serializers.ChoiceField(choices=Order.Status.choices)
    comment = serializers.CharField(required=False, allow_blank=True)


class OrderHistorySerializer(serializers.ModelSerializer):
    """
    Сериализатор для истории заказа.
    """
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = OrderHistory
        fields = [
            'id',
            'order',
            'user',
            'user_name',
            'action',
            'field',
            'old_value',
            'new_value',
            'description',
            'created_at'
        ]
        read_only_fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для платежа.
    """
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'payment_number',
            'order',
            'order_number',
            'amount',
            'payment_method',
            'payment_method_display',
            'status',
            'status_display',
            'transaction_id',
            'payment_date',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id', 'payment_number', 'created_at', 'updated_at',
            'payment_date'
        ]


class CreatePaymentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания платежа.
    """
    class Meta:
        model = Payment
        fields = [
            'order',
            'amount',
            'payment_method',
            'transaction_id'
        ]
    
    def validate_amount(self, value):
        """Валидация суммы платежа"""
        if value <= 0:
            raise serializers.ValidationError('Сумма платежа должна быть положительной')
        return value
    
    def validate(self, data):
        """Общая валидация"""
        order = data.get('order')
        amount = data.get('amount')
        
        if order and amount:
            # Проверяем, что сумма платежа не превышает остаток
            remaining = order.remaining_amount
            if amount > remaining:
                raise serializers.ValidationError({
                    'amount': f'Сумма платежа не может превышать остаток к оплате ({remaining})'
                })
        
        return data


class OrderStatsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики заказов.
    """
    total_orders = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    by_status = serializers.DictField(child=serializers.IntegerField())
    by_store = serializers.ListField(child=serializers.DictField())
    by_day = serializers.ListField(child=serializers.DictField())
    
    period = serializers.CharField()
    date_from = serializers.DateField()
    date_to = serializers.DateField()
from rest_framework import serializers
from .models import Cart, CartItem
from apps.products.serializers import ProductShortSerializer

class CartItemSerializer(serializers.ModelSerializer):
    """
    Сериализатор для товара в корзине.
    """
    product = ProductShortSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    unit_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        source='product.price',
        read_only=True
    )
    total_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )
    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )
    sku = serializers.CharField(
        source='product.sku',
        read_only=True
    )
    min_order_quantity = serializers.IntegerField(
        source='product.min_order_quantity',
        read_only=True
    )
    
    class Meta:
        model = CartItem
        fields = [
            'id',
            'product_id',
            'product',
            'product_name',
            'sku',
            'quantity',
            'unit_price',
            'total_price',
            'min_order_quantity',
            'added_at'
        ]
        read_only_fields = ['id', 'added_at']


class CartSerializer(serializers.ModelSerializer):
    """
    Сериализатор для корзины.
    """
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_amount = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        read_only=True
    )
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Cart
        fields = [
            'id',
            'user_email',
            'store',
            'items',
            'total_items',
            'total_amount',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AddToCartSerializer(serializers.Serializer):
    """
    Сериализатор для добавления товара в корзину.
    """
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(min_value=1, default=1)
    
    def validate(self, data):
        """
        Проверка данных перед добавлением в корзину.
        """
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise serializers.ValidationError(
                {'product_id': 'Товар не найден'}
            )
        
        # Проверяем минимальное количество
        if quantity < product.min_order_quantity:
            raise serializers.ValidationError({
                'quantity': f'Минимальное количество для заказа: {product.min_order_quantity}'
            })
        
        # Проверяем наличие товара (если есть поле in_stock)
        if hasattr(product, 'in_stock') and not product.in_stock:
            raise serializers.ValidationError(
                {'product_id': 'Товар временно отсутствует'}
            )
        
        data['product'] = product
        return data


class UpdateCartItemSerializer(serializers.Serializer):
    """
    Сериализатор для обновления количества товара.
    """
    quantity = serializers.IntegerField(min_value=1, required=True)
    
    def validate_quantity(self, value):
        """
        Проверка количества.
        """
        # Минимальная проверка, более сложная логика в view
        if value <= 0:
            raise serializers.ValidationError('Количество должно быть положительным')
        return value


class BatchUpdateCartSerializer(serializers.Serializer):
    """
    Сериализатор для массового обновления корзины.
    """
    items = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )
    
    def validate_items(self, value):
        """
        Проверка списка товаров.
        """
        if not value:
            raise serializers.ValidationError('Список товаров не может быть пустым')
        
        for item in value:
            if 'product_id' not in item:
                raise serializers.ValidationError(
                    'Каждый товар должен иметь product_id'
                )
        
        return value

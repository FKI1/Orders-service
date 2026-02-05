from rest_framework import serializers
from django.db.models import Avg
from .models import Product, Category, ProductImage, ProductReview
from apps.users.serializers import UserShortSerializer


class CategorySerializer(serializers.ModelSerializer):
    """
    Сериализатор для категории товаров.
    """
    products_count = serializers.IntegerField(read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    children = serializers.SerializerMethodField()
    breadcrumbs = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id',
            'name',
            'slug',
            'parent',
            'parent_name',
            'description',
            'image',
            'is_active',
            'display_order',
            'products_count',
            'children',
            'breadcrumbs',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'products_count']
    
    def get_children(self, obj):
        """Получить дочерние категории"""
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True).data
    
    def get_breadcrumbs(self, obj):
        """Получить хлебные крошки"""
        return obj.get_breadcrumbs()


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Сериализатор для изображения товара.
    """
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductImage
        fields = [
            'id',
            'product',
            'image',
            'image_url',
            'alt_text',
            'caption',
            'is_main',
            'display_order',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_image_url(self, obj):
        """Получить URL изображения"""
        if obj.image:
            return obj.image.url
        return None


class ProductReviewSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отзыва о товаре.
    """
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    helpful_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductReview
        fields = [
            'id',
            'product',
            'product_name',
            'user',
            'user_name',
            'rating',
            'title',
            'comment',
            'advantages',
            'disadvantages',
            'is_verified_purchase',
            'is_approved',
            'helpful_yes',
            'helpful_no',
            'helpful_percentage',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'helpful_yes', 
            'helpful_no', 'is_approved'
        ]
    
    def get_helpful_percentage(self, obj):
        """Процент полезности отзыва"""
        total = obj.helpful_yes + obj.helpful_no
        if total > 0:
            return (obj.helpful_yes / total) * 100
        return 0
    
    def validate_rating(self, value):
        """Валидация рейтинга"""
        if not 1 <= value <= 5:
            raise serializers.ValidationError('Рейтинг должен быть от 1 до 5')
        return value


class ProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для товара (краткий).
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.get_full_name', read_only=True)
    main_image = serializers.SerializerMethodField()
    available_quantity = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)
    discount_percent = serializers.FloatField(read_only=True)
    margin = serializers.FloatField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id',
            'sku',
            'name',
            'slug',
            'category',
            'category_name',
            'supplier',
            'supplier_name',
            'short_description',
            'price',
            'old_price',
            'unit',
            'min_order_quantity',
            'max_order_quantity',
            'step_quantity',
            'status',
            'status_display',
            'in_stock',
            'stock_quantity',
            'available_quantity',
            'is_low_stock',
            'is_out_of_stock',
            'rating',
            'total_reviews',
            'total_ordered',
            'main_image',
            'discount_percent',
            'margin',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'rating', 
            'total_reviews', 'total_ordered', 'available_quantity',
            'is_low_stock', 'is_out_of_stock', 'discount_percent', 'margin'
        ]
    
    def get_main_image(self, obj):
        """Получить основное изображение товара"""
        main_image = obj.images.filter(is_main=True).first()
        if main_image:
            return main_image.image.url
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детальной информации о товаре.
    """
    category = CategorySerializer(read_only=True)
    supplier = UserShortSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)
    discount_percent = serializers.FloatField(read_only=True)
    margin = serializers.FloatField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    specifications = serializers.JSONField(default=dict)
    
    class Meta:
        model = Product
        fields = [
            'id',
            'sku',
            'name',
            'slug',
            'category',
            'supplier',
            'short_description',
            'description',
            'price',
            'old_price',
            'cost_price',
            'unit',
            'weight',
            'dimensions',
            'min_order_quantity',
            'max_order_quantity',
            'step_quantity',
            'status',
            'status_display',
            'in_stock',
            'stock_quantity',
            'reserved_quantity',
            'available_quantity',
            'min_stock_level',
            'is_low_stock',
            'is_out_of_stock',
            'specifications',
            'rating',
            'total_reviews',
            'total_ordered',
            'images',
            'discount_percent',
            'margin',
            'created_at',
            'updated_at',
            'published_at'
        ]
        read_only_fields = '__all__'


class CreateProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания товара.
    """
    class Meta:
        model = Product
        fields = [
            'sku',
            'name',
            'category',
            'short_description',
            'description',
            'price',
            'old_price',
            'cost_price',
            'unit',
            'weight',
            'dimensions',
            'min_order_quantity',
            'max_order_quantity',
            'step_quantity',
            'status',
            'stock_quantity',
            'min_stock_level',
            'specifications'
        ]
    
    def validate_sku(self, value):
        """Валидация артикула"""
        if Product.objects.filter(sku=value).exists():
            raise serializers.ValidationError('Товар с таким артикулом уже существует')
        return value
    
    def validate_price(self, value):
        """Валидация цены"""
        if value <= 0:
            raise serializers.ValidationError('Цена должна быть положительной')
        return value
    
    def validate_min_order_quantity(self, value):
        """Валидация минимального количества"""
        if value <= 0:
            raise serializers.ValidationError('Минимальное количество должно быть положительным')
        return value
    
    def validate_stock_quantity(self, value):
        """Валидация количества на складе"""
        if value < 0:
            raise serializers.ValidationError('Количество на складе не может быть отрицательным')
        return value


class UpdateProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления товара.
    """
    class Meta:
        model = Product
        fields = [
            'name',
            'category',
            'short_description',
            'description',
            'price',
            'old_price',
            'cost_price',
            'unit',
            'weight',
            'dimensions',
            'min_order_quantity',
            'max_order_quantity',
            'step_quantity',
            'status',
            'stock_quantity',
            'min_stock_level',
            'specifications'
        ]
    
    def validate_price(self, value):
        """Валидация цены"""
        if value <= 0:
            raise serializers.ValidationError('Цена должна быть положительной')
        return value
    
    def validate_stock_quantity(self, value):
        """Валидация количества на складе"""
        if value < 0:
            raise serializers.ValidationError('Количество на складе не может быть отрицательным')
        return value


class ProductStatsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики товара.
    """
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    sku = serializers.CharField()
    
    # Продажи
    total_ordered = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_order_quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Наличие
    stock_quantity = serializers.IntegerField()
    reserved_quantity = serializers.IntegerField()
    available_quantity = serializers.IntegerField()
    is_low_stock = serializers.BooleanField()
    
    # Цены
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    old_price = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    cost_price = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    margin = serializers.FloatField(allow_null=True)
    
    # Рейтинги
    rating = serializers.FloatField()
    total_reviews = serializers.IntegerField()
    
    # Даты
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    last_ordered = serializers.DateTimeField(allow_null=True)
    
    # По периодам
    today_ordered = serializers.IntegerField()
    week_ordered = serializers.IntegerField()
    month_ordered = serializers.IntegerField()

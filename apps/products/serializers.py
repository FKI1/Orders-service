from rest_framework import serializers
from django.db.models import Avg
from .models import Product, Category, ProductImage, ProductReview, ProductSpecification
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



class ProductSpecificationSerializer(serializers.ModelSerializer):
    """
    Сериализатор для спецификации товара.
    """
    dimensions_text = serializers.CharField(read_only=True)
    weight_text = serializers.CharField(read_only=True)
    features_list = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductSpecification
        fields = [
            'id',
            'product',
            
            # Основные характеристики
            'brand',
            'manufacturer',
            'country_of_origin',
            'warranty',
            
            # Физические характеристики
            'weight_netto',
            'weight_brutto',
            'weight_text',
            'length',
            'width',
            'height',
            'dimensions_text',
            
            # Материалы и состав
            'material',
            'composition',
            'color',
            
            # Технические характеристики
            'power',
            'voltage',
            'frequency',
            'energy_class',
            
            # Эксплуатация
            'operating_temperature',
            'humidity_range',
            'ip_rating',
            
            # Комплектация
            'package_contents',
            'accessories',
            
            # Сертификация
            'certification',
            'gost',
            
            # Сроки
            'shelf_life',
            'production_date',
            'expiry_date',
            
            # Динамические характеристики
            'attributes',
            
            # Документация
            'manual_file',
            'specification_file',
            'drawing_file',
            
            # Видео
            'video_url',
            'video_file',
            
            # Дополнительно
            'features',
            'features_list',
            'restrictions',
            
            # Метаданные
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_features_list(self, obj):
        """Получить список особенностей"""
        return obj.get_features_list()
    
    def validate(self, data):
        """
        Валидация спецификации.
        """
        # Проверка дат
        if data.get('production_date') and data.get('expiry_date'):
            if data['production_date'] >= data['expiry_date']:
                raise serializers.ValidationError({
                    'expiry_date': 'Срок годности должен быть позже даты производства'
                })
        
        # Проверка веса
        if data.get('weight_netto') and data.get('weight_brutto'):
            if data['weight_netto'] > data['weight_brutto']:
                raise serializers.ValidationError({
                    'weight_netto': 'Вес нетто не может быть больше веса брутто'
                })
        
        return data


class ProductSpecificationCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания спецификации товара.
    """
    class Meta:
        model = ProductSpecification
        exclude = ['created_at', 'updated_at']
    
    def validate(self, data):
        """
        Валидация при создании.
        """
        # Проверяем, не существует ли уже спецификация для этого товара
        product = data.get('product')
        if product and ProductSpecification.objects.filter(product=product).exists():
            raise serializers.ValidationError({
                'product': 'Спецификация для этого товара уже существует'
            })
        
        return super().validate(data)


class ProductSpecificationUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления спецификации товара.
    """
    class Meta:
        model = ProductSpecification
        exclude = ['product', 'created_at', 'updated_at']
        extra_kwargs = {
            field: {'required': False}
            for field in [
                'brand', 'manufacturer', 'country_of_origin', 'warranty',
                'weight_netto', 'weight_brutto', 'length', 'width', 'height',
                'material', 'composition', 'color', 'power', 'voltage',
                'frequency', 'energy_class', 'operating_temperature',
                'humidity_range', 'ip_rating', 'package_contents', 'accessories',
                'certification', 'gost', 'shelf_life', 'production_date',
                'expiry_date', 'attributes', 'manual_file', 'specification_file',
                'drawing_file', 'video_url', 'video_file', 'features', 'restrictions'
            ]
        }
    
    def validate(self, data):
        """
        Валидация при обновлении.
        """
        # Проверка дат
        if data.get('production_date') and data.get('expiry_date'):
            if data['production_date'] >= data['expiry_date']:
                raise serializers.ValidationError({
                    'expiry_date': 'Срок годности должен быть позже даты производства'
                })
        
        # Проверка веса
        if data.get('weight_netto') and data.get('weight_brutto'):
            if data['weight_netto'] > data['weight_brutto']:
                raise serializers.ValidationError({
                    'weight_netto': 'Вес нетто не может быть больше веса брутто'
                })
        
        return data


class ProductSpecificationDetailSerializer(serializers.ModelSerializer):
    """
    Детальный сериализатор для спецификации товара.
    """
    dimensions_text = serializers.CharField(read_only=True)
    weight_text = serializers.CharField(read_only=True)
    features_list = serializers.SerializerMethodField()
    
    # Группированные характеристики
    basic_info = serializers.SerializerMethodField()
    physical_info = serializers.SerializerMethodField()
    technical_info = serializers.SerializerMethodField()
    operational_info = serializers.SerializerMethodField()
    packaging_info = serializers.SerializerMethodField()
    documents_info = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductSpecification
        fields = [
            'id',
            'product',
            'basic_info',
            'physical_info',
            'technical_info',
            'operational_info',
            'packaging_info',
            'documents_info',
            'attributes',
            'features_list',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_features_list(self, obj):
        """Получить список особенностей"""
        return obj.get_features_list()
    
    def get_basic_info(self, obj):
        """Основная информация о товаре"""
        return {
            'brand': obj.brand,
            'manufacturer': obj.manufacturer,
            'country_of_origin': obj.country_of_origin,
            'warranty': obj.warranty,
            'material': obj.material,
            'color': obj.color,
            'composition': obj.composition
        }
    
    def get_physical_info(self, obj):
        """Физические характеристики"""
        return {
            'weight_netto': obj.weight_netto,
            'weight_brutto': obj.weight_brutto,
            'weight_text': obj.weight_text,
            'length': obj.length,
            'width': obj.width,
            'height': obj.height,
            'dimensions_text': obj.dimensions_text
        }
    
    def get_technical_info(self, obj):
        """Технические характеристики"""
        return {
            'power': obj.power,
            'voltage': obj.voltage,
            'frequency': obj.frequency,
            'energy_class': obj.energy_class,
            'ip_rating': obj.ip_rating
        }
    
    def get_operational_info(self, obj):
        """Эксплуатационные характеристики"""
        return {
            'operating_temperature': obj.operating_temperature,
            'humidity_range': obj.humidity_range,
            'shelf_life': obj.shelf_life,
            'production_date': obj.production_date,
            'expiry_date': obj.expiry_date
        }
    
    def get_packaging_info(self, obj):
        """Информация об упаковке и комплектации"""
        return {
            'package_contents': obj.package_contents,
            'accessories': obj.accessories
        }
    
    def get_documents_info(self, obj):
        """Документация и ссылки"""
        return {
            'certification': obj.certification,
            'gost': obj.gost,
            'manual_file': obj.manual_file.url if obj.manual_file else None,
            'specification_file': obj.specification_file.url if obj.specification_file else None,
            'drawing_file': obj.drawing_file.url if obj.drawing_file else None,
            'video_url': obj.video_url,
            'video_file': obj.video_file.url if obj.video_file else None
        }


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
    Включает категорию, поставщика, изображения и спецификацию.
    """
    category = CategorySerializer(read_only=True)
    supplier = UserShortSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    specification = ProductSpecificationSerializer(read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)
    discount_percent = serializers.FloatField(read_only=True)
    margin = serializers.FloatField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reviews = serializers.SerializerMethodField()
    reviews_summary = serializers.SerializerMethodField()
    absolute_url = serializers.CharField(source='get_absolute_url', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id',
            'sku',
            'name',
            'slug',
            'absolute_url',
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
            'rating',
            'total_reviews',
            'total_ordered',
            'total_views',
            'images',
            'specification',
            'reviews',
            'reviews_summary',
            'discount_percent',
            'margin',
            'created_at',
            'updated_at',
            'published_at'
        ]
        read_only_fields = '__all__'
    
    def get_reviews(self, obj):
        """Получить последние отзывы о товаре"""
        reviews = obj.reviews.filter(is_approved=True)[:5]
        return ProductReviewSerializer(reviews, many=True).data
    
    def get_reviews_summary(self, obj):
        """Получить сводку по отзывам"""
        reviews = obj.reviews.filter(is_approved=True)
        
        # Распределение по рейтингам
        rating_distribution = {}
        for i in range(1, 6):
            count = reviews.filter(rating=i).count()
            rating_distribution[str(i)] = count
        
        return {
            'total': reviews.count(),
            'average_rating': float(obj.rating),
            'distribution': rating_distribution
        }


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
    
    def validate(self, data):
        """Дополнительная валидация"""
        # Проверка цены и старой цены
        if data.get('old_price') and data.get('price'):
            if data['old_price'] <= data['price']:
                raise serializers.ValidationError({
                    'old_price': 'Старая цена должна быть больше текущей цены'
                })
        
        # Проверка себестоимости
        if data.get('cost_price') and data.get('price'):
            if data['cost_price'] >= data['price']:
                raise serializers.ValidationError({
                    'cost_price': 'Себестоимость должна быть меньше розничной цены'
                })
        
        return data


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
        extra_kwargs = {
            field: {'required': False}
            for field in fields
        }
    
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
    
    def validate(self, data):
        """Дополнительная валидация"""
        # Проверка цены и старой цены
        if data.get('old_price') and data.get('price'):
            if data['old_price'] <= data['price']:
                raise serializers.ValidationError({
                    'old_price': 'Старая цена должна быть больше текущей цены'
                })
        
        # Проверка себестоимости
        if data.get('cost_price') and data.get('price'):
            if data['cost_price'] >= data['price']:
                raise serializers.ValidationError({
                    'cost_price': 'Себестоимость должна быть меньше розничной цены'
                })
        
        return data


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
    
    # Просмотры
    total_views = serializers.IntegerField()
    
    # Даты
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    last_ordered = serializers.DateTimeField(allow_null=True)
    
    # По периодам
    today_ordered = serializers.IntegerField()
    week_ordered = serializers.IntegerField()
    month_ordered = serializers.IntegerField()


class ProductListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка товаров (оптимизированный).
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    main_image = serializers.SerializerMethodField()
    price_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id',
            'sku',
            'name',
            'slug',
            'category_name',
            'short_description',
            'price',
            'old_price',
            'price_display',
            'main_image',
            'rating',
            'total_reviews',
            'in_stock',
            'is_low_stock',
            'discount_percent',
            'created_at'
        ]
        read_only_fields = fields
    
    def get_main_image(self, obj):
        """Получить основное изображение товара"""
        main_image = obj.images.filter(is_main=True).first()
        if main_image:
            return main_image.image.url
        return None
    
    def get_price_display(self, obj):
        """Форматирование цены для отображения"""
        return {
            'current': float(obj.price),
            'old': float(obj.old_price) if obj.old_price else None,
            'currency': '₽',
            'discount': obj.discount_percent
        }
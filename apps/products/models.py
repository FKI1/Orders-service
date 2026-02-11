from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import uuid


class Category(models.Model):
    """
    Категория товаров.
    """
    name = models.CharField(
        max_length=255,
        verbose_name=_('Название категории')
    )
    
    slug = models.SlugField(
        max_length=255,
        unique=True,
        verbose_name=_('URL-идентификатор')
    )
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Родительская категория')
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_('Описание категории')
    )
    
    image = models.ImageField(
        upload_to='categories/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Изображение категории')
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Активна')
    )
    
    display_order = models.IntegerField(
        default=0,
        verbose_name=_('Порядок отображения')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления')
    )
    
    class Meta:
        verbose_name = _('Категория')
        verbose_name_plural = _('Категории')
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['parent']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def products_count(self):
        """Количество товаров в категории (включая подкатегории)"""
        return self.get_all_products().count()
    
    def get_all_products(self):
        """Получить все товары категории и подкатегорий"""
        from django.db.models import Q
        
        # Получаем все подкатегории
        subcategories = self.get_all_subcategories()
        
        # Ищем товары в этой категории и всех подкатегориях
        return Product.objects.filter(
            Q(category=self) | Q(category__in=subcategories)
        ).distinct()
    
    def get_all_subcategories(self):
        """Получить все подкатегории (рекурсивно)"""
        subcategories = []
        
        def get_children(category):
            children = category.children.all()
            for child in children:
                subcategories.append(child)
                get_children(child)
        
        get_children(self)
        return subcategories
    
    def get_breadcrumbs(self):
        """Получить путь к категории (хлебные крошки)"""
        breadcrumbs = []
        current = self
        
        while current:
            breadcrumbs.insert(0, {
                'id': current.id,
                'name': current.name,
                'slug': current.slug
            })
            current = current.parent
        
        return breadcrumbs


class Product(models.Model):
    """
    Модель товара.
    """
    class ProductStatus(models.TextChoices):
        DRAFT = 'draft', _('Черновик')
        ACTIVE = 'active', _('Активен')
        INACTIVE = 'inactive', _('Неактивен')
        ARCHIVED = 'archived', _('В архиве')
    
    # Основная информация
    sku = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Артикул (SKU)'),
        help_text=_('Уникальный код товара')
    )
    
    name = models.CharField(
        max_length=255,
        verbose_name=_('Название товара')
    )
    
    slug = models.SlugField(
        max_length=255,
        unique=True,
        verbose_name=_('URL-идентификатор')
    )
    
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name=_('Категория')
    )
    
    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name=_('Поставщик'),
        limit_choices_to={'role': 'supplier'}
    )
    
    # Описание
    short_description = models.TextField(
        blank=True,
        verbose_name=_('Краткое описание'),
        help_text=_('Краткое описание для списков товаров')
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_('Полное описание'),
        help_text=_('Подробное описание товара')
    )
    
    # Цена и характеристики
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_('Цена'),
        help_text=_('Цена за единицу товара')
    )
    
    old_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Старая цена'),
        help_text=_('Цена до скидки (для отображения перечеркнутой цены)')
    )
    
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Себестоимость'),
        help_text=_('Закупочная цена у поставщика')
    )
    
    unit = models.CharField(
        max_length=50,
        default='шт',
        verbose_name=_('Единица измерения'),
        help_text=_('шт, кг, литр и т.д.')
    )
    
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_('Вес (кг)')
    )
    
    dimensions = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Габариты'),
        help_text=_('Длина x Ширина x Высота (см)')
    )
    
    # Ограничения по заказу
    min_order_quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Минимальное количество заказа'),
        help_text=_('Минимальное количество для заказа')
    )
    
    max_order_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Максимальное количество заказа'),
        help_text=_('Максимальное количество для одного заказа')
    )
    
    step_quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Шаг количества'),
        help_text=_('Кратность заказа (например, можно заказывать только кратно 10)')
    )
    
    # Наличие и статус
    status = models.CharField(
        max_length=20,
        choices=ProductStatus.choices,
        default=ProductStatus.DRAFT,
        verbose_name=_('Статус товара')
    )
    
    in_stock = models.BooleanField(
        default=True,
        verbose_name=_('В наличии')
    )
    
    stock_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Количество на складе')
    )
    
    reserved_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Зарезервировано')
    )
    
    min_stock_level = models.PositiveIntegerField(
        default=10,
        verbose_name=_('Минимальный остаток'),
        help_text=_('При достижении этого уровня товар помечается как "Мало на складе"')
    )
    
    # Технические характеристики (JSON поле для гибкости)
    specifications = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Характеристики'),
        help_text=_('Дополнительные характеристики в формате JSON')
    )
    
    # Рейтинги и статистика
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        verbose_name=_('Рейтинг')
    )
    
    total_reviews = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Количество отзывов')
    )
    
    total_ordered = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Всего заказано')
    )
    
    total_views = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Количество просмотров')
    )
    
    # Даты
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления')
    )
    
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Дата публикации')
    )
    
    class Meta:
        verbose_name = _('Товар')
        verbose_name_plural = _('Товары')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['slug']),
            models.Index(fields=['category']),
            models.Index(fields=['supplier']),
            models.Index(fields=['status']),
            models.Index(fields=['in_stock']),
            models.Index(fields=['price']),
            models.Index(fields=['created_at']),
            models.Index(fields=['total_ordered']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    def save(self, *args, **kwargs):
        """Автоматическая установка даты публикации при активации"""
        if self.pk:
            old_status = Product.objects.get(pk=self.pk).status
            if old_status != self.ProductStatus.ACTIVE and self.status == self.ProductStatus.ACTIVE:
                self.published_at = timezone.now()
        elif self.status == self.ProductStatus.ACTIVE:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Валидация модели"""
        super().clean()
        
        # Проверка цен
        if self.old_price and self.old_price <= self.price:
            raise ValidationError({
                'old_price': _('Старая цена должна быть больше текущей цены')
            })
        
        if self.cost_price and self.cost_price >= self.price:
            raise ValidationError({
                'cost_price': _('Себестоимость должна быть меньше розничной цены')
            })
        
        # Проверка количества заказа
        if self.max_order_quantity and self.min_order_quantity > self.max_order_quantity:
            raise ValidationError({
                'min_order_quantity': _('Минимальное количество не может превышать максимальное')
            })
        
        if self.step_quantity < 1:
            raise ValidationError({
                'step_quantity': _('Шаг количества должен быть больше 0')
            })
    
    @property
    def available_quantity(self):
        """Доступное для заказа количество"""
        return max(0, self.stock_quantity - self.reserved_quantity)
    
    @property
    def is_low_stock(self):
        """Мало на складе"""
        return self.stock_quantity <= self.min_stock_level
    
    @property
    def is_out_of_stock(self):
        """Нет в наличии"""
        return self.stock_quantity == 0 or not self.in_stock
    
    @property
    def discount_percent(self):
        """Процент скидки (если есть старая цена)"""
        if self.old_price and self.old_price > self.price:
            discount = ((self.old_price - self.price) / self.old_price) * 100
            return round(discount, 1)
        return 0
    
    @property
    def margin(self):
        """Маржинальность (если указана себестоимость)"""
        if self.cost_price and self.cost_price > 0:
            margin = ((self.price - self.cost_price) / self.cost_price) * 100
            return round(margin, 1)
        return None
    
    def reserve_quantity(self, quantity):
        """
        Зарезервировать количество товара.
        """
        if quantity > self.available_quantity:
            raise ValueError(f'Недостаточно товара. Доступно: {self.available_quantity}')
        
        self.reserved_quantity += quantity
        self.save(update_fields=['reserved_quantity'])
    
    def release_quantity(self, quantity):
        """
        Освободить зарезервированное количество.
        """
        if quantity > self.reserved_quantity:
            raise ValueError(f'Нельзя освободить больше, чем зарезервировано')
        
        self.reserved_quantity -= quantity
        self.save(update_fields=['reserved_quantity'])
    
    def update_stock(self, quantity):
        """
        Обновить количество на складе.
        """
        if quantity < 0:
            raise ValueError('Количество не может быть отрицательным')
        
        old_quantity = self.stock_quantity
        self.stock_quantity = quantity
        self.in_stock = quantity > 0
        
        self.save(update_fields=['stock_quantity', 'in_stock'])
    
    def increment_views(self):
        """Увеличить счетчик просмотров"""
        self.total_views += 1
        self.save(update_fields=['total_views'])
    
    def get_related_products(self, limit=4):
        """
        Получить похожие товары.
        """
        return Product.objects.filter(
            category=self.category,
            status=Product.ProductStatus.ACTIVE,
            in_stock=True
        ).exclude(id=self.id).order_by('?')[:limit]
    
    def get_absolute_url(self):
        """Получить URL товара"""
        from django.urls import reverse
        return reverse('products:product-detail', kwargs={'slug': self.slug})


class ProductSpecification(models.Model):
    """
    Детальная спецификация товара.
    Отдельная модель для расширенной информации о товаре.
    """
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='specification',
        verbose_name=_('Товар')
    )
    
    brand = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Бренд'),
        help_text=_('Производитель или бренд товара')
    )
    
    manufacturer = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Производитель'),
        help_text=_('Название компании-производителя')
    )
    
    country_of_origin = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Страна производства'),
        help_text=_('Страна, где произведен товар')
    )
    
    warranty = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Гарантия'),
        help_text=_('Срок гарантии (например: "1 год", "24 месяца")')
    )

    weight_netto = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_('Вес нетто (кг)'),
        help_text=_('Вес товара без упаковки')
    )
    
    weight_brutto = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_('Вес брутто (кг)'),
        help_text=_('Вес товара с упаковкой')
    )
    
    length = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Длина (см)')
    )
    
    width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Ширина (см)')
    )
    
    height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Высота (см)')
    )
    
    material = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Материал'),
        help_text=_('Основной материал изготовления')
    )
    
    composition = models.TextField(
        blank=True,
        verbose_name=_('Состав'),
        help_text=_('Детальный состав (для продуктов, тканей и т.д.)')
    )
    
    color = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Цвет')
    )

    power = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Мощность'),
        help_text=_('Например: "100 Вт", "2.2 кВт"')
    )
    
    voltage = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Напряжение'),
        help_text=_('Например: "220-240 В", "12 В"')
    )
    
    frequency = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Частота'),
        help_text=_('Например: "50 Гц"')
    )
    
    energy_class = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Класс энергопотребления'),
        help_text=_('A++, A+, A, B, C, D, E, F, G')
    )
    
    operating_temperature = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Рабочая температура'),
        help_text=_('Диапазон рабочих температур')
    )
    
    humidity_range = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Влажность эксплуатации'),
        help_text=_('Диапазон допустимой влажности')
    )
    
    ip_rating = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Класс защиты (IP)'),
        help_text=_('Например: IP44, IP67')
    )
    
    package_contents = models.TextField(
        blank=True,
        verbose_name=_('Комплектация'),
        help_text=_('Что входит в комплект поставки')
    )
    
    accessories = models.TextField(
        blank=True,
        verbose_name=_('Аксессуары'),
        help_text=_('Дополнительные аксессуары (опционально)')
    )
    
    certification = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Сертификация'),
        help_text=_('Сертификаты соответствия, EAC, CE, RoHS и т.д.')
    )
    
    gost = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('ГОСТ'),
        help_text=_('Соответствие государственным стандартам')
    )
    
    shelf_life = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Срок годности'),
        help_text=_('Срок годности или хранения')
    )
    
    production_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Дата производства')
    )
    
    expiry_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Срок годности до')
    )
    
    attributes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Дополнительные характеристики'),
        help_text=_('Специфические для категории характеристики в формате JSON')
    )
    
    manual_file = models.FileField(
        upload_to='products/manuals/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Инструкция (PDF)'),
        help_text=_('Файл с инструкцией по эксплуатации')
    )
    
    specification_file = models.FileField(
        upload_to='products/specs/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Спецификация (PDF)'),
        help_text=_('Файл с детальной спецификацией')
    )
    
    drawing_file = models.FileField(
        upload_to='products/drawings/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Чертеж (PDF/DWG)'),
        help_text=_('Технический чертеж или схема')
    )
    
    features = models.TextField(
        blank=True,
        verbose_name=_('Ключевые особенности'),
        help_text=_='Список основных преимуществ, разделенных точкой с запятой'
    )
    
    restrictions = models.TextField(
        blank=True,
        verbose_name=_('Ограничения'),
        help_text=_='Ограничения по использованию, противопоказания'
    )
    

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания спецификации')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления спецификации')
    )
    
    class Meta:
        verbose_name = _('Спецификация товара')
        verbose_name_plural = _('Спецификации товаров')
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['brand']),
            models.Index(fields=['country_of_origin']),
        ]
    
    def __str__(self):
        return f"Спецификация: {self.product.name}"
    
    def clean(self):
        """Валидация модели"""
        super().clean()
        
        # Проверка дат
        if self.production_date and self.expiry_date:
            if self.production_date >= self.expiry_date:
                raise ValidationError({
                    'expiry_date': _('Срок годности должен быть позже даты производства')
                })
        
        # Проверка веса
        if self.weight_netto and self.weight_brutto:
            if self.weight_netto > self.weight_brutto:
                raise ValidationError({
                    'weight_netto': _('Вес нетто не может быть больше веса брутто')
                })
    
    @property
    def dimensions_text(self):
        """Текстовое представление габаритов"""
        dimensions = []
        if self.length:
            dimensions.append(f"{self.length} см")
        if self.width:
            dimensions.append(f"{self.width} см")
        if self.height:
            dimensions.append(f"{self.height} см")
        
        if len(dimensions) == 3:
            return f"{dimensions[0]} x {dimensions[1]} x {dimensions[2]}"
        elif dimensions:
            return ", ".join(dimensions)
        return ""
    
    @property
    def weight_text(self):
        """Текстовое представление веса"""
        if self.weight_brutto:
            return f"{self.weight_brutto} кг (брутто)"
        elif self.weight_netto:
            return f"{self.weight_netto} кг (нетто)"
        return ""
    
    def get_features_list(self):
        """Получить список особенностей"""
        if self.features:
            return [f.strip() for f in self.features.split(';') if f.strip()]
        return []
    
    def to_dict(self):
        """Преобразовать спецификацию в словарь (для API)"""
        return {
            'brand': self.brand,
            'manufacturer': self.manufacturer,
            'country_of_origin': self.country_of_origin,
            'warranty': self.warranty,
            'weight': self.weight_text,
            'dimensions': self.dimensions_text,
            'material': self.material,
            'composition': self.composition,
            'color': self.color,
            'power': self.power,
            'voltage': self.voltage,
            'energy_class': self.energy_class,
            'ip_rating': self.ip_rating,
            'package_contents': self.package_contents,
            'certification': self.certification,
            'shelf_life': self.shelf_life,
            'attributes': self.attributes,
            'video_url': self.video_url,
            'features': self.get_features_list(),
        }


class ProductImage(models.Model):
    """
    Изображение товара.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Товар')
    )
    
    image = models.ImageField(
        upload_to='products/%Y/%m/%d/',
        verbose_name=_('Изображение')
    )
    
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Альтернативный текст'),
        help_text=_('Текст для SEO и доступности')
    )
    
    caption = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Подпись')
    )
    
    is_main = models.BooleanField(
        default=False,
        verbose_name=_('Основное изображение')
    )
    
    display_order = models.IntegerField(
        default=0,
        verbose_name=_('Порядок отображения')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата добавления')
    )
    
    class Meta:
        verbose_name = _('Изображение товара')
        verbose_name_plural = _('Изображения товаров')
        ordering = ['display_order', '-is_main', 'created_at']
        indexes = [
            models.Index(fields=['product', 'is_main']),
        ]
    
    def __str__(self):
        return f"Изображение для {self.product.name}"
    
    def save(self, *args, **kwargs):
        """При установке основного изображения сбрасываем флаг у других"""
        if self.is_main:
            # Снимаем флаг у других изображений этого товара
            ProductImage.objects.filter(
                product=self.product,
                is_main=True
            ).exclude(id=self.id).update(is_main=False)
        
        super().save(*args, **kwargs)


class ProductReview(models.Model):
    """
    Отзыв о товаре.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('Товар')
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='product_reviews',
        verbose_name=_('Пользователь')
    )
    
    rating = models.PositiveIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        verbose_name=_('Оценка')
    )
    
    title = models.CharField(
        max_length=255,
        verbose_name=_('Заголовок отзыва')
    )
    
    comment = models.TextField(
        verbose_name=_('Текст отзыва')
    )
    
    advantages = models.TextField(
        blank=True,
        verbose_name=_('Достоинства')
    )
    
    disadvantages = models.TextField(
        blank=True,
        verbose_name=_('Недостатки')
    )
    
    is_verified_purchase = models.BooleanField(
        default=False,
        verbose_name=_('Подтвержденная покупка')
    )
    
    is_approved = models.BooleanField(
        default=False,
        verbose_name=_('Одобрен')
    )
    
    helpful_yes = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Полезно')
    )
    
    helpful_no = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Не полезно')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата отзыва')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления')
    )
    
    class Meta:
        verbose_name = _('Отзыв о товаре')
        verbose_name_plural = _('Отзывы о товарах')
        ordering = ['-created_at']
        unique_together = ['product', 'user']
        indexes = [
            models.Index(fields=['product', 'is_approved']),
            models.Index(fields=['rating']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Отзыв на {self.product.name} от {self.user}"
    
    def save(self, *args, **kwargs):
        """При сохранении обновляем рейтинг товара"""
        super().save(*args, **kwargs)
        
        # Пересчитываем средний рейтинг товара
        self.update_product_rating()
    
    def update_product_rating(self):
        """Обновить рейтинг товара"""
        reviews = self.product.reviews.filter(is_approved=True)
        if reviews.exists():
            avg_rating = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.product.rating = round(avg_rating, 2)
            self.product.total_reviews = reviews.count()
            self.product.save(update_fields=['rating', 'total_reviews'])
    
    @classmethod
    def recalculate_all_ratings(cls):
        """Пересчитать рейтинги для всех товаров"""
        from django.db.models import Avg
        
        products = Product.objects.all()
        for product in products:
            reviews = product.reviews.filter(is_approved=True)
            if reviews.exists():
                avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
                product.rating = round(avg_rating, 2)
                product.total_reviews = reviews.count()
            else:
                product.rating = 0
                product.total_reviews = 0
            product.save(update_fields=['rating', 'total_reviews'])
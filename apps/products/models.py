from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
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
        self.save()
    
    def release_quantity(self, quantity):
        """
        Освободить зарезервированное количество.
        """
        if quantity > self.reserved_quantity:
            raise ValueError(f'Нельзя освободить больше, чем зарезервировано')
        
        self.reserved_quantity -= quantity
        self.save()
    
    def update_stock(self, quantity):
        """
        Обновить количество на складе.
        """
        if quantity < 0:
            raise ValueError('Количество не может быть отрицательным')
        
        self.stock_quantity = quantity
        if self.stock_quantity == 0:
            self.in_stock = False
        else:
            self.in_stock = True
        
        self.save()
    
    def get_related_products(self, limit=4):
        """
        Получить похожие товары.
        """
        return Product.objects.filter(
            category=self.category,
            status=Product.ProductStatus.ACTIVE,
            in_stock=True
        ).exclude(id=self.id).order_by('?')[:limit]


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
    
    def __str__(self):
        return f"Отзыв на {self.product.name} от {self.user}"
    
    def save(self, *args, **kwargs):
        """При сохранении обновляем рейтинг товара"""
        super().save(*args, **kwargs)
        
        # Пересчитываем средний рейтинг товара
        reviews = self.product.reviews.filter(is_approved=True)
        if reviews.exists():
            avg_rating = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.product.rating = round(avg_rating, 2)
            self.product.total_reviews = reviews.count()
            self.product.save()
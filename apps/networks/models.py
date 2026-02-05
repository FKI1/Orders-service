"Розничная сеть"
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class RetailNetwork(models.Model):
    """
    Модель розничной сети.
    """
    name = models.CharField(
        max_length=255,
        verbose_name=_('Название сети'),
        help_text=_('Например: "Сеть супермаркетов Продукты"')
    )
    
    legal_name = models.CharField(
        max_length=255,
        verbose_name=_('Юридическое название'),
        help_text=_('Полное юридическое название компании')
    )
    
    tax_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('ИНН'),
        help_text=_('Идентификационный номер налогоплательщика')
    )
    
    legal_address = models.TextField(
        verbose_name=_('Юридический адрес'),
        blank=True
    )
    
    contact_email = models.EmailField(
        verbose_name=_('Контактный email'),
        help_text=_('Для официальной переписки')
    )
    
    contact_phone = models.CharField(
        max_length=20,
        verbose_name=_('Контактный телефон'),
        blank=True
    )
    
    website = models.URLField(
        verbose_name=_('Веб-сайт'),
        blank=True
    )
    
    description = models.TextField(
        verbose_name=_('Описание сети'),
        blank=True,
        help_text=_('Краткое описание деятельности сети')
    )
    
    # Настройки сети
    monthly_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Месячный бюджет'),
        help_text=_('Общий бюджет сети на месяц')
    )
    
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Минимальная сумма заказа'),
        help_text=_('Минимальная сумма для оформления заказа')
    )
    
    # Статусы
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Активна')
    )
    
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_('Верифицирована'),
        help_text=_('Сеть прошла проверку администрацией')
    )
    
    # Временные метки
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления')
    )
    
    # Связи
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_networks',
        verbose_name=_('Создатель')
    )
    
    administrators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='managed_networks',
        verbose_name=_('Администраторы сети'),
        blank=True,
        help_text=_('Пользователи с правами управления сетью')
    )
    
    class Meta:
        verbose_name = _('Розничная сеть')
        verbose_name_plural = _('Розничные сети')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['tax_id']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def stores_count(self):
        """Количество магазинов в сети"""
        return self.stores.count()
    
    @property
    def employees_count(self):
        """Количество сотрудников сети"""
        return self.employees.count()
    
    @property
    def total_orders(self):
        """Общее количество заказов сети"""
        from apps.orders.models import Order
        return Order.objects.filter(store__network=self).count()
    
    @property
    def monthly_spent(self):
        """Потрачено в текущем месяце"""
        from django.utils import timezone
        from django.db.models import Sum
        from apps.orders.models import Order
        
        today = timezone.now()
        first_day = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        spent = Order.objects.filter(
            store__network=self,
            created_at__gte=first_day,
            status__in=['approved', 'processing', 'delivered']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        return spent
    
    @property
    def budget_utilization(self):
        """Процент использования бюджета"""
        if self.monthly_budget == 0:
            return 0
        
        utilization = (self.monthly_spent / self.monthly_budget) * 100
        return round(utilization, 2)


class Store(models.Model):
    """
    Модель магазина (торговой точки сети).
    """
    class StoreType(models.TextChoices):
        SUPERMARKET = 'supermarket', _('Супермаркет')
        HYPERMARKET = 'hypermarket', _('Гипермаркет')
        CONVENIENCE = 'convenience', _('Магазин у дома')
        SPECIALTY = 'specialty', _('Специализированный магазин')
        WAREHOUSE = 'warehouse', _('Складской магазин')
        ONLINE = 'online', _('Онлайн-магазин')
    
    class StoreStatus(models.TextChoices):
        ACTIVE = 'active', _('Активен')
        INACTIVE = 'inactive', _('Неактивен')
        MAINTENANCE = 'maintenance', _('На обслуживании')
        CLOSED = 'closed', _('Закрыт')
    
    network = models.ForeignKey(
        RetailNetwork,
        on_delete=models.CASCADE,
        related_name='stores',
        verbose_name=_('Сеть')
    )
    
    name = models.CharField(
        max_length=255,
        verbose_name=_('Название магазина'),
        help_text=_('Например: "Супермаркет №1 на Ленина"')
    )
    
    store_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Код магазина'),
        help_text=_('Внутренний код магазина в сети')
    )
    
    store_type = models.CharField(
        max_length=20,
        choices=StoreType.choices,
        default=StoreType.SUPERMARKET,
        verbose_name=_('Тип магазина')
    )
    
    status = models.CharField(
        max_length=20,
        choices=StoreStatus.choices,
        default=StoreStatus.ACTIVE,
        verbose_name=_('Статус')
    )
    
    # Адрес
    address = models.TextField(
        verbose_name=_('Адрес')
    )
    
    city = models.CharField(
        max_length=100,
        verbose_name=_('Город')
    )
    
    region = models.CharField(
        max_length=100,
        verbose_name=_('Регион/Область')
    )
    
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Почтовый индекс')
    )
    
    # Координаты (для карт)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_('Широта')
    )
    
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_('Долгота')
    )
    
    # Контактная информация магазина
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Телефон магазина')
    )
    
    email = models.EmailField(
        blank=True,
        verbose_name=_('Email магазина')
    )
    
    # Характеристики магазина
    area = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Площадь (кв.м)'),
        help_text=_('Площадь торгового зала')
    )
    
    opening_hours = models.TextField(
        blank=True,
        verbose_name=_('Часы работы'),
        help_text=_('Формат: Пн-Пт: 9:00-21:00, Сб-Вс: 10:00-20:00')
    )
    
    # Бюджет магазина
    monthly_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Месячный бюджет магазина')
    )
    
    # Персонал
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_stores',
        verbose_name=_('Менеджер магазина'),
        limit_choices_to={'role__in': ['store_manager', 'network_admin']}
    )
    
    staff_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Количество сотрудников')
    )
    
    # Статистика (можно обновлять периодически)
    average_daily_traffic = models.IntegerField(
        default=0,
        verbose_name=_('Средняя дневная посещаемость')
    )
    
    average_check = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Средний чек')
    )
    
    # Временные метки
    opened_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Дата открытия')
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
        verbose_name = _('Магазин')
        verbose_name_plural = _('Магазины')
        ordering = ['network', 'city', 'name']
        indexes = [
            models.Index(fields=['network']),
            models.Index(fields=['city']),
            models.Index(fields=['region']),
            models.Index(fields=['status']),
            models.Index(fields=['store_code']),
        ]
        unique_together = ['network', 'store_code']
    
    def __str__(self):
        return f"{self.name} ({self.network.name})"
    
    @property
    def full_address(self):
        """Полный адрес магазина"""
        parts = []
        if self.postal_code:
            parts.append(self.postal_code)
        parts.extend([self.city, self.address])
        return ', '.join(filter(None, parts))
    
    @property
    def coordinates(self):
        """Координаты в формате для карт"""
        if self.latitude and self.longitude:
            return {'lat': float(self.latitude), 'lng': float(self.longitude)}
        return None
    
    @property
    def monthly_spent(self):
        """Потрачено в текущем месяце"""
        from django.utils import timezone
        from django.db.models import Sum
        from apps.orders.models import Order
        
        today = timezone.now()
        first_day = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        spent = Order.objects.filter(
            store=self,
            created_at__gte=first_day,
            status__in=['approved', 'processing', 'delivered']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        return spent
    
    @property
    def budget_utilization(self):
        """Процент использования бюджета"""
        if self.monthly_budget == 0:
            return 0
        
        utilization = (self.monthly_spent / self.monthly_budget) * 100
        return round(utilization, 2)
    
    @property
    def total_orders(self):
        """Общее количество заказов магазина"""
        from apps.orders.models import Order
        return Order.objects.filter(store=self).count()
    
    def get_employees(self):
        """Получить всех сотрудников магазина"""
        from apps.users.models import User
        return User.objects.filter(
            models.Q(store_manager=self) |
            models.Q(store_assignment__store=self)
        ).distinct()


class StoreAssignment(models.Model):
    """
    Назначение сотрудников на магазины.
    Позволяет одному сотруднику работать в нескольких магазинах.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='store_assignments',
        verbose_name=_('Сотрудник')
    )
    
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('Магазин')
    )
    
    role = models.CharField(
        max_length=50,
        verbose_name=_('Роль в магазине'),
        help_text=_('Например: "Старший продавец", "Кассир"')
    )
    
    is_primary = models.BooleanField(
        default=False,
        verbose_name=_('Основное место работы'),
        help_text=_('Это основной магазин сотрудника')
    )
    
    assigned_at = models.DateField(
        auto_now_add=True,
        verbose_name=_('Дата назначения')
    )
    
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='made_assignments',
        verbose_name=_('Назначил')
    )
    
    class Meta:
        verbose_name = _('Назначение на магазин')
        verbose_name_plural = _('Назначения на магазины')
        unique_together = ['user', 'store']
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.user} → {self.store}"


class NetworkSettings(models.Model):
    """
    Настройки сети.
    """
    network = models.OneToOneField(
        RetailNetwork,
        on_delete=models.CASCADE,
        related_name='settings',
        verbose_name=_('Сеть')
    )
    
    # Настройки заказов
    require_approval = models.BooleanField(
        default=True,
        verbose_name=_('Требовать подтверждение заказов'),
        help_text=_('Заказы требуют подтверждения администратором')
    )
    
    approval_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100000,
        verbose_name=_('Порог подтверждения'),
        help_text=_('Сумма заказа, выше которой требуется подтверждение')
    )
    
    max_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=500000,
        verbose_name=_('Максимальная сумма заказа')
    )
    
    # Настройки уведомлений
    notify_on_new_order = models.BooleanField(
        default=True,
        verbose_name=_('Уведомлять о новых заказах')
    )
    
    notify_on_order_status_change = models.BooleanField(
        default=True,
        verbose_name=_('Уведомлять об изменении статуса заказа')
    )
    
    notify_on_budget_threshold = models.BooleanField(
        default=True,
        verbose_name=_('Уведомлять при достижении порога бюджета')
    )
    
    budget_threshold_percent = models.IntegerField(
        default=80,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Порог бюджета (%)'),
        help_text=_('Процент использования бюджета для уведомления')
    )
    
    # Настройки интеграций
    allow_api_access = models.BooleanField(
        default=False,
        verbose_name=_('Разрешить доступ по API'),
        help_text=_('Разрешить интеграцию с внешними системами')
    )
    
    api_key = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('API ключ')
    )
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Настройки сети')
        verbose_name_plural = _('Настройки сетей')
    
    def __str__(self):
        return f"Настройки {self.network.name}"
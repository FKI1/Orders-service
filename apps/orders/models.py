from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import uuid


class Order(models.Model):
    """
    Модель заказа.
    """
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Черновик')
        PENDING = 'pending', _('На согласовании')
        APPROVED = 'approved', _('Подтвержден')
        PROCESSING = 'processing', _('В обработке')
        SHIPPED = 'shipped', _('Отправлен')
        DELIVERED = 'delivered', _('Доставлен')
        CANCELLED = 'cancelled', _('Отменен')
        REJECTED = 'rejected', _('Отклонен')
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', _('Ожидает оплаты')
        PAID = 'paid', _('Оплачен')
        PARTIALLY_PAID = 'partially_paid', _('Частично оплачен')
        FAILED = 'failed', _('Ошибка оплаты')
        REFUNDED = 'refunded', _('Возвращен')
    
    # Основная информация
    order_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        verbose_name=_('Номер заказа')
    )
    
    store = models.ForeignKey(
        'networks.Store',
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name=_('Магазин')
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_orders',
        verbose_name=_('Создатель заказа')
    )
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_orders',
        verbose_name=_('Подтвердил')
    )
    
    delivery_address = models.ForeignKey(
        'users.Address',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name=_('Адрес доставки'),
        help_text=_('Адрес доставки из профиля пользователя')
    )
    
    delivery_address_snapshot = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Снимок адреса доставки'),
        help_text=_('Копия адреса на момент оформления заказа (для истории)')
    )
    
    # Дополнительные поля для доставки
    delivery_instructions = models.TextField(
        blank=True,
        verbose_name=_('Инструкции по доставке'),
        help_text=_('Особые указания для курьера')
    )
    
    delivery_time_from = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_('Время доставки с')
    )
    
    delivery_time_to = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_('Время доставки до')
    )
    
    delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Дата доставки')
    )
    
    # Контактная информация получателя (дублируется из адреса)
    recipient_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Получатель')
    )
    
    recipient_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Телефон получателя')
    )
    
    
    # Статусы
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_('Статус заказа')
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name=_('Статус оплаты')
    )
    
    # Суммы
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Сумма товаров')
    )
    
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Сумма скидки')
    )
    
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Итоговая сумма')
    )
    
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Оплаченная сумма')
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
    
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Дата подтверждения')
    )
    
    shipped_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Дата отправки')
    )
    
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Дата доставки')
    )
    
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Дата отмены')
    )
    
    # Даты планирования
    required_delivery_date = models.DateField(
        verbose_name=_('Желаемая дата доставки')
    )
    
    estimated_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Расчетная дата доставки')
    )
    
    # Дополнительная информация
    notes = models.TextField(
        blank=True,
        verbose_name=_('Примечания'),
        help_text=_('Внутренние примечания к заказу')
    )
    
    cancellation_reason = models.TextField(
        blank=True,
        verbose_name=_('Причина отмены')
    )
    
    rejection_reason = models.TextField(
        blank=True,
        verbose_name=_('Причина отклонения')
    )
    
    # Метаданные
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Метаданные'),
        help_text=_('Дополнительные данные в формате JSON')
    )
    
    class Meta:
        verbose_name = _('Заказ')
        verbose_name_plural = _('Заказы')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['store']),
            models.Index(fields=['created_by']),
            models.Index(fields=['delivery_address']),
            models.Index(fields=['delivery_date']),
            models.Index(fields=['required_delivery_date']),
        ]
    
    def __str__(self):
        return f"Заказ {self.order_number}"
    
    def save(self, *args, **kwargs):
        """Генерация номера заказа при создании и обработка адреса доставки"""
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        if not self.pk and self.delivery_address:
            self.create_address_snapshot()
        
        # Обновляем даты при изменении статуса
        if self.pk:
            old_status = Order.objects.get(pk=self.pk).status
            if old_status != self.status:
                self.update_status_dates(old_status, self.status)
        
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Генерация уникального номера заказа"""
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4().hex[:6]).upper()
        return f"ORD-{date_str}-{random_str}"
    
    
    def create_address_snapshot(self):
        """
        Создать снимок адреса доставки на момент оформления заказа.
        Сохраняет копию адреса для истории, даже если адрес будет изменен/удален.
        """
        if self.delivery_address:
            self.delivery_address_snapshot = {
                'id': self.delivery_address.id,
                'full_address': self.delivery_address.full_address,
                'short_address': self.delivery_address.short_address,
                'address_type': self.delivery_address.address_type,
                'address_type_display': self.delivery_address.get_address_type_display(),
                'city': self.delivery_address.city,
                'street': self.delivery_address.street,
                'house': self.delivery_address.house,
                'apartment': self.delivery_address.apartment,
                'entrance': self.delivery_address.entrance,
                'floor': self.delivery_address.floor,
                'intercom': self.delivery_address.intercom,
                'recipient_name': self.delivery_address.recipient_name,
                'recipient_phone': self.delivery_address.recipient_phone,
                'comment': self.delivery_address.comment,
            }
            
            # Дублируем информацию о получателе
            self.recipient_name = self.delivery_address.recipient_name
            self.recipient_phone = self.delivery_address.recipient_phone
    
    def update_delivery_info(self, address=None, **kwargs):
        """
        Обновить информацию о доставке.
        """
        if address:
            self.delivery_address = address
            self.create_address_snapshot()
        
        # Обновляем дополнительные поля
        delivery_fields = ['delivery_instructions', 'delivery_time_from', 
                          'delivery_time_to', 'delivery_date']
        
        for field in delivery_fields:
            if field in kwargs:
                setattr(self, field, kwargs[field])
        
        self.save(update_fields=['delivery_address', 'delivery_address_snapshot',
                                'recipient_name', 'recipient_phone'] + delivery_fields)
    
    @property
    def delivery_address_display(self):
        """
        Получить отображаемый адрес доставки (из снимка или текущего адреса).
        """
        if self.delivery_address_snapshot:
            return self.delivery_address_snapshot.get('full_address', '')
        elif self.delivery_address:
            return self.delivery_address.full_address
        return ''
    
    @property
    def has_delivery_address(self):
        """Проверка наличия адреса доставки"""
        return bool(self.delivery_address or self.delivery_address_snapshot)
    
    @property
    def delivery_window(self):
        """Окно доставки (время)"""
        if self.delivery_time_from and self.delivery_time_to:
            return f"{self.delivery_time_from.strftime('%H:%M')} - {self.delivery_time_to.strftime('%H:%M')}"
        return ''
    
    
    def update_status_dates(self, old_status, new_status):
        """Обновление дат при изменении статуса"""
        now = timezone.now()
        
        if new_status == self.Status.APPROVED and old_status != self.Status.APPROVED:
            self.approved_at = now
        
        elif new_status == self.Status.SHIPPED and old_status != self.Status.SHIPPED:
            self.shipped_at = now
        
        elif new_status == self.Status.DELIVERED and old_status != self.Status.DELIVERED:
            self.delivered_at = now
        
        elif new_status == self.Status.CANCELLED and old_status != self.Status.CANCELLED:
            self.cancelled_at = now
    
    @property
    def remaining_amount(self):
        """Остаток к оплате"""
        return self.total_amount - self.paid_amount
    
    @property
    def is_paid(self):
        """Заказ полностью оплачен"""
        return self.payment_status == self.PaymentStatus.PAID
    
    @property
    def can_be_cancelled(self):
        """Можно ли отменить заказ"""
        return self.status in [
            self.Status.DRAFT,
            self.Status.PENDING,
            self.Status.APPROVED
        ]
    
    @property
    def items_count(self):
        """Количество позиций в заказе"""
        return self.items.count()
    
    @property
    def total_quantity(self):
        """Общее количество товаров в заказе"""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    def calculate_totals(self):
        """Пересчитать суммы заказа"""
        from django.db.models import Sum
        
        # Сумма товаров
        items_total = self.items.aggregate(
            total=Sum('total')
        )['total'] or 0
        
        # Пока используем простой расчет
        self.subtotal = items_total
        self.total_amount = self.subtotal - self.discount_amount
        
        # Если оплачено больше, чем сумма заказа
        if self.paid_amount > self.total_amount:
            self.paid_amount = self.total_amount
        
        # Обновляем статус оплаты
        self.update_payment_status()
        
        self.save(update_fields=['subtotal', 'total_amount', 'paid_amount', 'payment_status'])
    
    def update_payment_status(self):
        """Обновить статус оплаты"""
        if self.paid_amount == 0:
            self.payment_status = self.PaymentStatus.PENDING
        elif self.paid_amount >= self.total_amount:
            self.payment_status = self.PaymentStatus.PAID
        elif self.paid_amount > 0:
            self.payment_status = self.PaymentStatus.PARTIALLY_PAID
        else:
            self.payment_status = self.PaymentStatus.PENDING
    
    def clean(self):
        """Валидация модели"""
        super().clean()
        
        # Проверка дат доставки
        if self.required_delivery_date and self.required_delivery_date < timezone.now().date():
            raise ValidationError({
                'required_delivery_date': _('Желаемая дата доставки не может быть в прошлом')
            })
        
        if self.delivery_date and self.delivery_date < timezone.now().date():
            raise ValidationError({
                'delivery_date': _('Дата доставки не может быть в прошлом')
            })
        
        # Проверка времени доставки
        if self.delivery_time_from and self.delivery_time_to:
            if self.delivery_time_from >= self.delivery_time_to:
                raise ValidationError({
                    'delivery_time_to': _('Время "до" должно быть позже времени "с"')
                })


class OrderItem(models.Model):
    """
    Позиция в заказе.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Заказ')
    )
    
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name=_('Товар')
    )
    
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Количество')
    )
    
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Цена за единицу')
    )
    
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Общая сумма')
    )
    
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_('Скидка %')
    )
    
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Сумма скидки')
    )
    
    product_snapshot = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Снимок товара'),
        help_text=_('Копия данных товара на момент заказа')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата добавления')
    )
    
    class Meta:
        verbose_name = _('Позиция заказа')
        verbose_name_plural = _('Позиции заказа')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
        ]
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        """Автоматический расчет суммы и скидки"""
        
        if not self.pk:
            # Создаем снимок товара при первом сохранении
            self.create_product_snapshot()
        
        # Расчет суммы со скидкой
        if self.discount_percent > 0:
            self.discount_amount = (self.unit_price * self.discount_percent / 100) * self.quantity
            self.total = (self.unit_price * self.quantity) - self.discount_amount
        else:
            self.discount_amount = 0
            self.total = self.unit_price * self.quantity
        
        super().save(*args, **kwargs)
        
        # Пересчитываем суммы заказа
        if self.order:
            self.order.calculate_totals()
    
    
    def create_product_snapshot(self):
        """
        Создать снимок товара на момент заказа.
        Сохраняет копию данных товара для истории.
        """
        if self.product:
            self.product_snapshot = {
                'id': self.product.id,
                'sku': self.product.sku,
                'name': self.product.name,
                'category': self.product.category.name if self.product.category else None,
                'supplier': self.product.supplier.email if self.product.supplier else None,
                'unit': self.product.unit,
                'image': self.product.images.filter(is_main=True).first().image.url if self.product.images.filter(is_main=True).exists() else None,
            }
    
    def delete(self, *args, **kwargs):
        """При удалении пересчитываем суммы заказа"""
        order = self.order
        super().delete(*args, **kwargs)
        
        if order:
            order.calculate_totals()


class OrderHistory(models.Model):
    """
    История изменений заказа.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name=_('Заказ')
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_changes',
        verbose_name=_('Пользователь')
    )
    
    action = models.CharField(
        max_length=100,
        verbose_name=_('Действие')
    )
    
    field = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Измененное поле')
    )
    
    old_value = models.TextField(
        blank=True,
        verbose_name=_('Старое значение')
    )
    
    new_value = models.TextField(
        blank=True,
        verbose_name=_('Новое значение')
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_('Описание изменения')
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP адрес')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Метаданные')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата изменения')
    )
    
    class Meta:
        verbose_name = _('История заказа')
        verbose_name_plural = _('История заказов')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['created_at']),
            models.Index(fields=['action']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.order.order_number} - {self.action}"
    
    @classmethod
    def log_change(cls, order, user, action, field=None, old_value=None, 
                   new_value=None, description=None, request=None):
        """
        Удобный метод для логирования изменений.
        """
        history = cls(
            order=order,
            user=user,
            action=action,
            field=field,
            old_value=str(old_value) if old_value else '',
            new_value=str(new_value) if new_value else '',
            description=description or '',
        )
        
        if request:
            history.ip_address = request.META.get('REMOTE_ADDR')
            history.user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        history.save()
        return history


class Payment(models.Model):
    """
    Платеж по заказу.
    """
    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = 'bank_transfer', _('Банковский перевод')
        CARD = 'card', _('Банковская карта')
        CASH = 'cash', _('Наличные')
        ONLINE = 'online', _('Онлайн-платеж')
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', _('Ожидает')
        PROCESSING = 'processing', _('В обработке')
        COMPLETED = 'completed', _('Завершен')
        FAILED = 'failed', _('Неуспешен')
        REFUNDED = 'refunded', _('Возвращен')
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name=_('Заказ')
    )
    
    payment_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Номер платежа')
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Сумма платежа')
    )
    
    payment_method = models.CharField(
        max_length=50,
        choices=PaymentMethod.choices,
        verbose_name=_('Способ оплаты')
    )
    
    status = models.CharField(
        max_length=50,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name=_('Статус платежа')
    )
    
    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('ID транзакции')
    )
    
    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Дата оплаты')
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_payments',
        verbose_name=_('Создал')
    )
    
    commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Комиссия'),
        help_text=_('Комиссия платежной системы')
    )
    
    fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Сбор'),
        help_text=_('Дополнительный сбор')
    )
    
    currency = models.CharField(
        max_length=3,
        default='RUB',
        verbose_name=_('Валюта')
    )
    
    exchange_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=1.0,
        verbose_name=_('Курс обмена')
    )
    
    gateway_response = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Ответ платежного шлюза')
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Метаданные')
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
        verbose_name = _('Платеж')
        verbose_name_plural = _('Платежи')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_number']),
            models.Index(fields=['order']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['transaction_id']),
        ]
    
    def __str__(self):
        return f"Платеж {self.payment_number} - {self.amount} {self.currency}"
    
    def save(self, *args, **kwargs):
        """Генерация номера платежа и обновление заказа"""
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        
        if self.status == self.PaymentStatus.COMPLETED and not self.payment_date:
            self.payment_date = timezone.now()
            
            # Обновляем оплаченную сумму в заказе
            self.order.paid_amount += self.amount
            self.order.update_payment_status()
            self.order.save(update_fields=['paid_amount', 'payment_status'])
        
        super().save(*args, **kwargs)
    
    def generate_payment_number(self):
        """Генерация номера платежа"""
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4().hex[:6]).upper()
        return f"PAY-{date_str}-{random_str}"
    
    @property
    def total_amount_with_fees(self):
        """Общая сумма с комиссией и сборами"""
        return self.amount + self.commission + self.fee
    
    def process_refund(self, amount=None):
        """
        Обработка возврата платежа.
        """
        refund_amount = amount if amount else self.amount
        
        if refund_amount > self.amount:
            raise ValidationError('Сумма возврата не может превышать сумму платежа')
        
        # Создаем запись о возврате (можно создать отдельную модель Refund)
        self.status = self.PaymentStatus.REFUNDED
        self.save()
        
        # Обновляем сумму в заказе
        self.order.paid_amount -= refund_amount
        self.order.update_payment_status()
        self.order.save()
        
        return refund_amount
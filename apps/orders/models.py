from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
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
        ]
    
    def __str__(self):
        return f"Заказ {self.order_number}"
    
    def save(self, *args, **kwargs):
        """Генерация номера заказа при создании"""
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
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
        
        self.save()
    
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
        """Автоматический расчет суммы"""
        if self.unit_price and self.quantity:
            self.total = self.unit_price * self.quantity
        super().save(*args, **kwargs)
        
        # Пересчитываем суммы заказа
        if self.order:
            self.order.calculate_totals()
    
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
        ]
    
    def __str__(self):
        return f"{self.order.order_number} - {self.action}"


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
    
    def __str__(self):
        return f"Платеж {self.payment_number} - {self.amount}"
    
    def save(self, *args, **kwargs):
        """Генерация номера платежа и обновление заказа"""
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        
        if self.status == self.PaymentStatus.COMPLETED and not self.payment_date:
            self.payment_date = timezone.now()
            
            # Обновляем оплаченную сумму в заказе
            self.order.paid_amount += self.amount
            self.order.update_payment_status()
            self.order.save()
        
        super().save(*args, **kwargs)
    
    def generate_payment_number(self):
        """Генерация номера платежа"""
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4().hex[:6]).upper()
        return f"PAY-{date_str}-{random_str}"
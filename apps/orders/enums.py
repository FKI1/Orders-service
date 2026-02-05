"""
Перечисления (enums) для приложения orders.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class OrderStatus(models.TextChoices):
    """
    Статусы заказа.
    """
    DRAFT = 'draft', _('Черновик')
    PENDING = 'pending', _('На согласовании')
    APPROVED = 'approved', _('Подтвержден')
    PROCESSING = 'processing', _('В обработке')
    SHIPPED = 'shipped', _('Отправлен')
    DELIVERED = 'delivered', _('Доставлен')
    CANCELLED = 'cancelled', _('Отменен')
    REJECTED = 'rejected', _('Отклонен')


class PaymentStatus(models.TextChoices):
    """
    Статусы оплаты.
    """
    PENDING = 'pending', _('Ожидает оплаты')
    PAID = 'paid', _('Оплачен')
    PARTIALLY_PAID = 'partially_paid', _('Частично оплачен')
    FAILED = 'failed', _('Ошибка оплаты')
    REFUNDED = 'refunded', _('Возвращен')


class PaymentMethod(models.TextChoices):
    """
    Способы оплаты.
    """
    BANK_TRANSFER = 'bank_transfer', _('Банковский перевод')
    CARD = 'card', _('Банковская карта')
    CASH = 'cash', _('Наличные')
    ONLINE = 'online', _('Онлайн-платеж')


class OrderAction(models.TextChoices):
    """
    Действия с заказом для истории.
    """
    CREATED = 'created', _('Создан')
    UPDATED = 'updated', _('Обновлен')
    STATUS_CHANGED = 'status_changed', _('Изменен статус')
    PAYMENT_ADDED = 'payment_added', _('Добавлен платеж')
    CANCELLED = 'cancelled', _('Отменен')
    APPROVED = 'approved', _('Подтвержден')
    SHIPPED = 'shipped', _('Отправлен')
    DELIVERED = 'delivered', _('Доставлен')

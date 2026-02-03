from django.db import models
from django.conf import settings
from apps.products.models import Product

class Cart(models.Model):
    """
    Модель корзины пользователя.
    У каждого пользователя одна активная корзина.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name='Пользователь'
    )
    store = models.ForeignKey(
        'stores.Store',  # Предполагаем, что есть приложение stores
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Магазин'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f'Корзина пользователя {self.user.email}'
    
    @property
    def total_items(self):
        """Общее количество товаров в корзине"""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    @property
    def total_amount(self):
        """Общая сумма корзины"""
        total = 0
        for item in self.items.all():
            total += item.total_price
        return total
    
    def clear(self):
        """Очистить корзину"""
        self.items.all().delete()
        self.save()


class CartItem(models.Model):
    """
    Товар в корзине.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Корзина'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name='Товар'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name='Количество'
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Добавлено')
    
    class Meta:
        verbose_name = 'Товар в корзине'
        verbose_name_plural = 'Товары в корзине'
        unique_together = ['cart', 'product']  # Один товар - одна запись
        ordering = ['-added_at']
    
    def __str__(self):
        return f'{self.product.name} x {self.quantity}'
    
    @property
    def unit_price(self):
        """Цена за единицу товара"""
        return self.product.price
    
    @property
    def total_price(self):
        """Общая цена за товар (цена * количество)"""
        return self.unit_price * self.quantity
    
    def save(self, *args, **kwargs):
        """Проверяем минимальное количество при сохранении"""
        if self.quantity < self.product.min_order_quantity:
            self.quantity = self.product.min_order_quantity
        super().save(*args, **kwargs)

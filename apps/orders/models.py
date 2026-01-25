"Заголовок заказа"
class Order(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('pending', 'На согласовании'),
        ('approved', 'Подтвержден'),
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True) # Уникальный номер заказа
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name='orders') # Для какого магазина заказ
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_orders') # Кто создал заказ
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft') # Текущее состояние заказа в workflow
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0) # Рассчитывается автоматически из OrderItem
    created_at = models.DateTimeField(auto_now_add=True) # Дата создания
    updated_at = models.DateTimeField(auto_now=True) # Дата последнего изменения
    delivery_date = models.DateField() # Планируемая дата доставки
    notes = models.TextField(blank=True) # Комментарии
    
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

"Строки заказа"
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT) # Какой товар заказывается
    quantity = models.PositiveIntegerField() # Количество товара
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Цена на момент заказа
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
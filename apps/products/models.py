"Модель категории товаров"
class Category(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

"Модель товаров"
class Product(models.Model):
    name = models.CharField(max_length=255) # Название товара
    sku = models.CharField(max_length=100, unique=True) # Артикул
    category = models.ForeignKey(Category, on_delete=models.PROTECT) # Категория
    description = models.TextField(blank=True) # Описание
    unit = models.CharField(max_length=50)  # Единица измерения
    price = models.DecimalField(max_digits=10, decimal_places=2) # Цена
    supplier = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'supplier'}) # Поставщик
    min_order_quantity = models.PositiveIntegerField(default=1) # Мин. заказ
    
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
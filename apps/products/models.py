# apps/products/models.py
class Category(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

class Product(models.Model):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=50)  # шт, кг, литр и т.д.
    price = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'supplier'})
    min_order_quantity = models.PositiveIntegerField(default=1)
    
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
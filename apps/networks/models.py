"Розничная сеть"
class RetailNetwork(models.Model):
    name = models.CharField(max_length=255) # Торговое название
    legal_name = models.CharField(max_length=255) # Юридическое название
    tax_id = models.CharField(max_length=20, unique=True) # ИНН/налоговый номер
    contact_email = models.EmailField() # Контактный email
    contact_phone = models.CharField(max_length=20) # Контактный телефон
    
    class Meta:
        verbose_name = 'Розничная сеть'
        verbose_name_plural = 'Розничные сети'

"Магазин"
class Store(models.Model):
    network = models.ForeignKey(RetailNetwork, on_delete=models.CASCADE, related_name='stores') # Связь с родительской сетью
    name = models.CharField(max_length=255) # Название конкретного магазина
    address = models.TextField() # Полный физический адрес магазина
    city = models.CharField(max_length=100) # Расположения магазина
    region = models.CharField(max_length=100) # Регион/область/край
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'store_manager'}) # Связь с менеджером магазина
    
    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'
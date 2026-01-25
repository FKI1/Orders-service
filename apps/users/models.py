from django.contrib.auth.models import AbstractUser

"Система ролей"
class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('supplier', 'Поставщик'),
        ('network_admin', 'Администратор сети'),
        ('store_manager', 'Менеджер магазина'),
        ('buyer', 'Закупщик'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    phone = models.CharField(max_length=20, blank=True) # Телефон пользователя
    company = models.ForeignKey('networks.RetailNetwork', on_delete=models.SET_NULL, null=True, blank=True) # Связь с розничной сетью
    
    "Для читаемости имени в админке Django"
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

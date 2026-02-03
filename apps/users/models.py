from django.contrib.auth.models import AbstractUser
from django.db import models

"Система ролей"
class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('supplier', 'Поставщик'),
        ('network_admin', 'Администратор сети'),
        ('store_manager', 'Менеджер магазина'),
        ('buyer', 'Закупщик'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=Role.BUYER)

    phone = models.CharField(max_length=20, blank=True) # Телефон пользователя
    company = models.ForeignKey('networks.RetailNetwork', on_delete=models.SET_NULL, null=True, blank=True) # Связь с розничной сетью
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    "Для читаемости имени в админке Django"
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

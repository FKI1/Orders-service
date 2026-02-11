from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta


class CustomUserManager(BaseUserManager):
    """
    Кастомный менеджер пользователей с email вместо username.
    """
    def create_user(self, email, password=None, **extra_fields):
        """
        Создает и сохраняет пользователя с указанным email и паролем.
        """
        if not email:
            raise ValueError(_('Email обязателен'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Создает и сохраняет суперпользователя.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        extra_fields.setdefault('email_verified', True)  # Суперпользователь сразу верифицирован
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Суперпользователь должен иметь is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Суперпользователь должен иметь is_superuser=True'))
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Кастомная модель пользователя.
    """
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Администратор')
        SUPPLIER = 'supplier', _('Поставщик')
        NETWORK_ADMIN = 'network_admin', _('Администратор сети')
        STORE_MANAGER = 'store_manager', _('Менеджер магазина')
        BUYER = 'buyer', _('Закупщик')
    
    # Убираем username, используем email как уникальный идентификатор
    username = None
    email = models.EmailField(
        _('email address'),
        unique=True,
        help_text=_('Будет использоваться для входа в систему')
    )
    
    # Роли и персональная информация
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.BUYER,
        verbose_name=_('Роль')
    )
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=_("Номер телефона должен быть в формате: '+79991234567'. Максимум 15 цифр.")
    )
    
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        verbose_name=_('Телефон')
    )
    
    company_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Название компании')
    )
    
    position = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Должность')
    )
    
    # Статусы
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Активный')
    )
    
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_('Верифицирован')
    )
    email_verified = models.BooleanField(
        default=False,
        verbose_name=_('Email подтвержден')
    )
    
    email_verification_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Токен подтверждения email')
    )
    
    email_verification_sent_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Дата отправки подтверждения email')
    )
    
    # Настройки
    receive_notifications = models.BooleanField(
        default=True,
        verbose_name=_('Получать уведомления')
    )
    
    # Связи
    company = models.ForeignKey(
        'networks.RetailNetwork',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        verbose_name=_('Компания')
    )
    
    # Менеджер
    objects = CustomUserManager()
    
    # Поле для аутентификации
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
            models.Index(fields=['company']),
            models.Index(fields=['date_joined']),
            models.Index(fields=['email_verified']),
            models.Index(fields=['email_verification_token']),
        
        ]
    
    def __str__(self):
        return self.email
    
    def clean(self):
        """Валидация модели"""
        super().clean()
        
        # Проверяем соответствие роли и компании
        if self.role in [User.Role.NETWORK_ADMIN, User.Role.STORE_MANAGER, User.Role.BUYER]:
            if not self.company:
                raise ValidationError(
                    _('Для ролей сети/магазина должна быть указана компания')
                )
    
    @property
    def full_name(self):
        """Полное имя пользователя"""
        return f"{self.first_name} {self.last_name}".strip() or self.email
    
    @property
    def short_name(self):
        """Короткое имя пользователя"""
        if self.first_name:
            return self.first_name
        return self.email.split('@')[0]
    

    @property
    def is_email_verification_expired(self):
        """Проверка, истек ли срок действия токена подтверждения (24 часа)"""
        if not self.email_verification_sent_at:
            return True
        return timezone.now() > self.email_verification_sent_at + timedelta(hours=24)
    
    def generate_verification_token(self):
        """Генерация нового токена подтверждения"""
        import secrets
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_sent_at = timezone.now()
        return self.email_verification_token

    
    def is_supplier(self):
        """Проверка, является ли пользователь поставщиком"""
        return self.role == self.Role.SUPPLIER
    
    def is_network_admin(self):
        """Проверка, является ли пользователь администратором сети"""
        return self.role == self.Role.NETWORK_ADMIN
    
    def is_store_manager(self):
        """Проверка, является ли пользователь менеджером магазина"""
        return self.role == self.Role.STORE_MANAGER
    
    def is_buyer(self):
        """Проверка, является ли пользователь закупщиком"""
        return self.role == self.Role.BUYER


class UserProfile(models.Model):
    """
    Дополнительный профиль пользователя.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('Пользователь')
    )
    
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Аватар')
    )
    
    bio = models.TextField(
        blank=True,
        verbose_name=_('О себе'),
        help_text=_('Краткая информация о пользователе')
    )
    
    # Настройки уведомлений
    notify_email = models.BooleanField(
        default=True,
        verbose_name=_('Уведомления по email')
    )
    
    notify_sms = models.BooleanField(
        default=False,
        verbose_name=_('Уведомления по SMS')
    )
    
    notify_push = models.BooleanField(
        default=True,
        verbose_name=_('Push уведомления')
    )
    
    # Настройки отображения
    language = models.CharField(
        max_length=10,
        default='ru',
        choices=[
            ('ru', 'Русский'),
            ('en', 'English'),
        ],
        verbose_name=_('Язык интерфейса')
    )
    
    timezone = models.CharField(
        max_length=50,
        default='Europe/Moscow',
        verbose_name=_('Часовой пояс')
    )
    
    currency = models.CharField(
        max_length=3,
        default='RUB',
        choices=[
            ('RUB', 'Рубли'),
            ('USD', 'Доллары'),
            ('EUR', 'Евро'),
        ],
        verbose_name=_('Валюта')
    )
    
    # Настройки безопасности
    two_factor_auth = models.BooleanField(
        default=False,
        verbose_name=_('Двухфакторная аутентификация')
    )
    
    last_password_change = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Последняя смена пароля')
    )
    
    # Статистика
    login_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Количество входов')
    )
    
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('Последний IP входа')
    )
    
    # Метаданные
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания профиля')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления профиля')
    )
    
    class Meta:
        verbose_name = _('Профиль пользователя')
        verbose_name_plural = _('Профили пользователей')
    
    def __str__(self):
        return f"Профиль {self.user.email}"
    
    def save(self, *args, **kwargs):
        """Создание профиля при создании пользователя"""
        if not self.pk:
            # Автоматически создаем профиль при создании пользователя
            try:
                existing_profile = UserProfile.objects.get(user=self.user)
                self.pk = existing_profile.pk
            except UserProfile.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)


class Address(models.Model):
    """
    Модель адреса доставки пользователя.
    """
    class AddressType(models.TextChoices):
        HOME = 'home', _('Домашний')
        WORK = 'work', _('Рабочий')
        OTHER = 'other', _('Другой')
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name=_('Пользователь')
    )
    
    # Тип адреса
    address_type = models.CharField(
        max_length=10,
        choices=AddressType.choices,
        default=AddressType.HOME,
        verbose_name=_('Тип адреса')
    )
    
    # Основные поля адреса
    city = models.CharField(
        max_length=100,
        verbose_name=_('Город')
    )
    
    street = models.CharField(
        max_length=200,
        verbose_name=_('Улица')
    )
    
    house = models.CharField(
        max_length=20,
        verbose_name=_('Дом')
    )
    
    apartment = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Квартира/офис')
    )
    
    # Дополнительная информация
    entrance = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Подъезд')
    )
    
    floor = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Этаж')
    )
    
    intercom = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Домофон')
    )
    
    # Контактная информация для доставки
    recipient_name = models.CharField(
        max_length=100,
        verbose_name=_('Получатель')
    )
    
    recipient_phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')],
        verbose_name=_('Телефон получателя')
    )
    
    # Комментарий курьеру
    comment = models.TextField(
        max_length=500,
        blank=True,
        verbose_name=_('Комментарий')
    )
    
    # Флаг "Адрес по умолчанию"
    is_default = models.BooleanField(
        default=False,
        verbose_name=_('По умолчанию')
    )
    
    # Метаданные
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления')
    )
    
    class Meta:
        verbose_name = _('Адрес доставки')
        verbose_name_plural = _('Адреса доставки')
        ordering = ['-is_default', '-created_at']
        unique_together = ['user', 'city', 'street', 'house', 'apartment']
        indexes = [
            models.Index(fields=['user', 'is_default']),
            models.Index(fields=['city', 'street']),
            models.Index(fields=['recipient_phone']),
        ]
    
    def __str__(self):
        address = f"{self.city}, {self.street}, д.{self.house}"
        if self.apartment:
            address += f", кв.{self.apartment}"
        return address
    
    def save(self, *args, **kwargs):
        """Сохранение с обработкой адреса по умолчанию"""
        # Если устанавливаем этот адрес как default, сбрасываем default у других адресов
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
    
    @property
    def full_address(self):
        """Полный адрес одной строкой"""
        parts = [self.city, self.street, f"д.{self.house}"]
        if self.apartment:
            parts.append(f"кв.{self.apartment}")
        if self.entrance:
            parts.append(f"под.{self.entrance}")
        if self.floor:
            parts.append(f"эт.{self.floor}")
        return ", ".join(parts)
    
    @property
    def short_address(self):
        """Краткий адрес (без доп. информации)"""
        address = f"{self.city}, {self.street}, д.{self.house}"
        if self.apartment:
            address += f", кв.{self.apartment}"
        return address


class UserActivity(models.Model):
    """
    История активности пользователя.
    """
    class ActivityType(models.TextChoices):
        LOGIN = 'login', _('Вход в систему')
        LOGOUT = 'logout', _('Выход из системы')
        PASSWORD_CHANGE = 'password_change', _('Смена пароля')
        PROFILE_UPDATE = 'profile_update', _('Обновление профиля')
        ORDER_CREATE = 'order_create', _('Создание заказа')
        ORDER_UPDATE = 'order_update', _('Обновление заказа')
        PRODUCT_VIEW = 'product_view', _('Просмотр товара')
        CART_UPDATE = 'cart_update', _('Обновление корзины')
        EMAIL_VERIFICATION = 'email_verification', _('Подтверждение email')
        EMAIL_VERIFICATION_SENT = 'email_verification_sent', _('Отправка подтверждения email')
        ADDRESS_CREATE = 'address_create', _('Добавление адреса')
        ADDRESS_UPDATE = 'address_update', _('Обновление адреса')
        ADDRESS_DELETE = 'address_delete', _('Удаление адреса')
        ADDRESS_SET_DEFAULT = 'address_set_default', _('Установка адреса по умолчанию')
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name=_('Пользователь')
    )
    
    activity_type = models.CharField(
        max_length=50,
        choices=ActivityType.choices,
        verbose_name=_('Тип активности')
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_('Описание активности')
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
        verbose_name=_('Метаданные'),
        help_text=_('Дополнительные данные в формате JSON')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата активности')
    )
    
    class Meta:
        verbose_name = _('Активность пользователя')
        verbose_name_plural = _('Активности пользователей')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_activity_type_display()}"


class PasswordResetToken(models.Model):
    """
    Токен для сброса пароля.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
        verbose_name=_('Пользователь')
    )
    
    token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Токен')
    )
    
    is_used = models.BooleanField(
        default=False,
        verbose_name=_('Использован')
    )
    
    expires_at = models.DateTimeField(
        verbose_name=_('Действует до')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    
    class Meta:
        verbose_name = _('Токен сброса пароля')
        verbose_name_plural = _('Токены сброса пароля')
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Токен для {self.user.email}"
    
    def is_valid(self):
        """Проверка валидности токена"""
        return not self.is_used and self.expires_at > timezone.now()
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    User, UserProfile, Address, 
    UserActivity, PasswordResetToken
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Админ-панель для модели User.
    """
    # Поля для отображения в списке пользователей
    list_display = [
        'email', 'full_name_display', 'role', 'company_link',
        'email_verified_status', 'is_verified', 'is_active',
        'date_joined_display', 'addresses_count'
    ]
    
    list_filter = [
        'role', 'is_active', 'is_verified', 'email_verified',
        'receive_notifications', 'date_joined'
    ]
    
    search_fields = ['email', 'first_name', 'last_name', 'phone', 'company_name']
    
    ordering = ['-date_joined']
    
    # Поля для редактирования
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Персональная информация'), {
            'fields': (
                'first_name', 'last_name', 'phone',
                'company_name', 'position', 'role', 'company'
            )
        }),
        (_('Статусы и верификация'), {
            'fields': (
                'is_active', 'is_verified', 'email_verified',
                'email_verification_token', 'email_verification_sent_at',
                'receive_notifications'
            ),
            'classes': ('wide',)
        }),
        (_('Разрешения'), {
            'fields': (
                'is_staff', 'is_superuser', 'groups', 'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        (_('Даты'), {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    # Поля для создания нового пользователя
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2',
                'first_name', 'last_name', 'role',
                'company', 'is_active', 'email_verified'
            ),
        }),
    )
    
    readonly_fields = [
        'email_verification_token', 'email_verification_sent_at',
        'last_login', 'date_joined'
    ]
    
    list_per_page = 50
    
    def get_queryset(self, request):
        """Оптимизация запросов с подгрузкой связанных данных"""
        queryset = super().get_queryset(request)
        return queryset.select_related('company').prefetch_related('addresses')
    
    # Кастомные методы для отображения
    def full_name_display(self, obj):
        """Отображение полного имени"""
        name = obj.full_name
        if obj.email_verified:
            return format_html('{} ✅', name)
        return name
    full_name_display.short_description = _('Имя')
    full_name_display.admin_order_field = 'first_name'
    
    def company_link(self, obj):
        """Ссылка на компанию пользователя"""
        if obj.company:
            url = reverse('admin:networks_retailnetwork_change', args=[obj.company.id])
            return format_html('<a href="{}">{}</a>', url, obj.company.name)
        return obj.company_name or '—'
    company_link.short_description = _('Компания')
    company_link.admin_order_field = 'company__name'
    
    def email_verified_status(self, obj):
        """Статус подтверждения email с иконкой"""
        if obj.email_verified:
            return format_html('<span style="color: green;">✅ Подтвержден</span>')
        elif obj.email_verification_token:
            if obj.is_email_verification_expired:
                return format_html('<span style="color: orange;">⏱ Истек</span>')
            return format_html('<span style="color: orange;">⏳ Ожидает</span>')
        return format_html('<span style="color: gray;">❌ Не подтвержден</span>')
    email_verified_status.short_description = _('Email подтверждение')
    email_verified_status.admin_order_field = 'email_verified'
    
    def date_joined_display(self, obj):
        """Форматирование даты регистрации"""
        return obj.date_joined.strftime('%d.%m.%Y %H:%M')
    date_joined_display.short_description = _('Дата регистрации')
    date_joined_display.admin_order_field = 'date_joined'
    
    def addresses_count(self, obj):
        """Количество адресов пользователя"""
        count = obj.addresses.count()
        url = reverse('admin:users_address_changelist') + f'?user__id__exact={obj.id}'
        return format_html('<a href="{}">{} адр.</a>', url, count)
    addresses_count.short_description = _('Адреса')
    
    def activities_count(self, obj):
        """Количество действий пользователя"""
        return obj.activities.count()
    activities_count.short_description = _('Действий')
    
    # Действия над списком пользователей
    actions = ['activate_users', 'deactivate_users', 'verify_emails', 'resend_verification']
    
    def activate_users(self, request, queryset):
        """Активировать выбранных пользователей"""
        updated = queryset.update(is_active=True)
        self.message_user(request, _('Активировано {} пользователей').format(updated))
    activate_users.short_description = _('Активировать выбранных пользователей')
    
    def deactivate_users(self, request, queryset):
        """Деактивировать выбранных пользователей"""
        updated = queryset.update(is_active=False)
        self.message_user(request, _('Деактивировано {} пользователей').format(updated))
    deactivate_users.short_description = _('Деактивировать выбранных пользователей')
    
    def verify_emails(self, request, queryset):
        """Подтвердить email выбранных пользователей"""
        updated = queryset.update(
            email_verified=True,
            email_verification_token=None,
            email_verification_sent_at=None
        )
        self.message_user(request, _('Email подтвержден для {} пользователей').format(updated))
    verify_emails.short_description = _('Подтвердить email')
    
    def resend_verification(self, request, queryset):
        """Отправить повторное подтверждение (имитация)"""
        # В реальном проекте здесь будет вызов сервиса отправки
        count = queryset.filter(email_verified=False).count()
        self.message_user(
            request, 
            _('Запрос на повторную отправку для {} пользователей').format(count)
        )
    resend_verification.short_description = _('Отправить повторное подтверждение')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Админ-панель для профилей пользователей.
    """
    list_display = [
        'user_link', 'avatar_preview', 'language', 
        'currency', 'two_factor_auth', 'login_count'
    ]
    
    list_filter = ['language', 'currency', 'two_factor_auth', 'timezone']
    
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'bio']
    
    readonly_fields = [
        'login_count', 'last_login_ip', 'last_password_change',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        (_('Пользователь'), {
            'fields': ('user',)
        }),
        (_('Аватар и информация'), {
            'fields': ('avatar', 'bio')
        }),
        (_('Настройки уведомлений'), {
            'fields': ('notify_email', 'notify_sms', 'notify_push')
        }),
        (_('Настройки интерфейса'), {
            'fields': ('language', 'timezone', 'currency')
        }),
        (_('Безопасность'), {
            'fields': ('two_factor_auth', 'last_password_change')
        }),
        (_('Статистика'), {
            'fields': ('login_count', 'last_login_ip', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('user')
    
    def user_link(self, obj):
        """Ссылка на пользователя"""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = _('Пользователь')
    user_link.admin_order_field = 'user__email'
    
    def avatar_preview(self, obj):
        """Превью аватара"""
        if obj.avatar:
            return format_html(
                '<img src="{}" style="max-height: 40px; max-width: 40px; border-radius: 50%;" />',
                obj.avatar.url
            )
        return '—'
    avatar_preview.short_description = _('Аватар')


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """
    Админ-панель для адресов доставки.
    """
    list_display = [
        'id', 'user_link', 'short_address_display', 
        'address_type', 'recipient_name', 'recipient_phone',
        'is_default_status', 'created_at_display'
    ]
    
    list_filter = [
        'address_type', 'is_default', 'city', 
        'created_at', 'updated_at'
    ]
    
    search_fields = [
        'user__email', 'city', 'street', 'house',
        'recipient_name', 'recipient_phone'
    ]
    
    readonly_fields = ['created_at', 'updated_at', 'full_address_display']
    
    fieldsets = (
        (_('Пользователь'), {
            'fields': ('user',)
        }),
        (_('Тип адреса'), {
            'fields': ('address_type', 'is_default')
        }),
        (_('Адрес'), {
            'fields': (
                'city', 'street', 'house', 'apartment',
                'entrance', 'floor', 'intercom'
            )
        }),
        (_('Получатель'), {
            'fields': ('recipient_name', 'recipient_phone', 'comment')
        }),
        (_('Дополнительно'), {
            'fields': ('full_address_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 50
    list_select_related = ['user']
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('user')
    
    def user_link(self, obj):
        """Ссылка на пользователя"""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = _('Пользователь')
    user_link.admin_order_field = 'user__email'
    
    def short_address_display(self, obj):
        """Краткое отображение адреса"""
        return obj.short_address
    short_address_display.short_description = _('Адрес')
    short_address_display.admin_order_field = 'city'
    
    def full_address_display(self, obj):
        """Полное отображение адреса"""
        return format_html(
            '<strong>Полный адрес:</strong> {}<br>'
            '<strong>Получатель:</strong> {}<br>'
            '<strong>Телефон:</strong> {}<br>'
            '<strong>Комментарий:</strong> {}',
            obj.full_address,
            obj.recipient_name,
            obj.recipient_phone,
            obj.comment or '—'
        )
    full_address_display.short_description = _('Детальная информация')
    
    def is_default_status(self, obj):
        """Статус адреса по умолчанию с иконкой"""
        if obj.is_default:
            return format_html('<span style="color: green;">✅ Основной</span>')
        return format_html('<span style="color: gray;">—</span>')
    is_default_status.short_description = _('По умолчанию')
    is_default_status.admin_order_field = 'is_default'
    
    def created_at_display(self, obj):
        """Форматирование даты создания"""
        return obj.created_at.strftime('%d.%m.%Y %H:%M')
    created_at_display.short_description = _('Дата создания')
    created_at_display.admin_order_field = 'created_at'
    
    # Действия над списком адресов
    actions = ['set_as_default', 'remove_default']
    
    def set_as_default(self, request, queryset):
        """Установить выбранные адреса как основные"""
        for address in queryset:
            address.is_default = True
            address.save()
        self.message_user(request, _('Адреса установлены как основные'))
    set_as_default.short_description = _('Установить как основной адрес')
    
    def remove_default(self, request, queryset):
        """Убрать статус основного адреса"""
        updated = queryset.update(is_default=False)
        self.message_user(request, _('Статус основного убран у {} адресов').format(updated))
    remove_default.short_description = _('Убрать статус основного')


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """
    Админ-панель для активности пользователей.
    """
    list_display = [
        'user_link', 'activity_type_display', 
        'description_short', 'ip_address', 'created_at_display'
    ]
    
    list_filter = ['activity_type', 'created_at']
    
    search_fields = [
        'user__email', 'description', 
        'ip_address', 'metadata'
    ]
    
    readonly_fields = [
        'user', 'activity_type', 'description',
        'ip_address', 'user_agent', 'metadata', 'created_at'
    ]
    
    fieldsets = (
        (_('Пользователь и действие'), {
            'fields': ('user', 'activity_type', 'description')
        }),
        (_('Техническая информация'), {
            'fields': ('ip_address', 'user_agent', 'metadata')
        }),
        (_('Время'), {
            'fields': ('created_at',)
        }),
    )
    
    list_per_page = 100
    list_select_related = ['user']
    
    def has_add_permission(self, request):
        """Запрещаем добавление записей вручную"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Запрещаем изменение записей"""
        return False
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('user')
    
    def user_link(self, obj):
        """Ссылка на пользователя"""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = _('Пользователь')
    user_link.admin_order_field = 'user__email'
    
    def activity_type_display(self, obj):
        """Отображение типа активности с цветом"""
        colors = {
            'login': 'green',
            'logout': 'gray',
            'password_change': 'orange',
            'profile_update': 'blue',
            'order_create': 'purple',
            'order_update': 'purple',
            'product_view': 'teal',
            'cart_update': 'brown',
            'email_verification': 'cyan',
            'email_verification_sent': 'cyan',
            'address_create': 'indigo',
            'address_update': 'indigo',
            'address_delete': 'red',
            'address_set_default': 'indigo',
        }
        color = colors.get(obj.activity_type, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_activity_type_display()
        )
    activity_type_display.short_description = _('Тип активности')
    
    def description_short(self, obj):
        """Укороченное описание"""
        if len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description or '—'
    description_short.short_description = _('Описание')
    
    def created_at_display(self, obj):
        """Форматирование даты"""
        return obj.created_at.strftime('%d.%m.%Y %H:%M:%S')
    created_at_display.short_description = _('Дата и время')
    created_at_display.admin_order_field = 'created_at'


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """
    Админ-панель для токенов сброса пароля.
    """
    list_display = [
        'user_link', 'token_short', 'status_display',
        'expires_at_display', 'created_at_display'
    ]
    
    list_filter = ['is_used', 'expires_at', 'created_at']
    
    search_fields = ['user__email', 'token']
    
    readonly_fields = ['user', 'token', 'expires_at', 'created_at']
    
    fieldsets = (
        (_('Пользователь'), {
            'fields': ('user',)
        }),
        (_('Токен'), {
            'fields': ('token', 'is_used', 'expires_at')
        }),
        (_('Дата создания'), {
            'fields': ('created_at',)
        }),
    )
    
    list_select_related = ['user']
    
    def has_add_permission(self, request):
        """Запрещаем добавление токенов вручную"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Запрещаем изменение токенов"""
        return False
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('user')
    
    def user_link(self, obj):
        """Ссылка на пользователя"""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = _('Пользователь')
    user_link.admin_order_field = 'user__email'
    
    def token_short(self, obj):
        """Укороченный токен"""
        return obj.token[:20] + '...' if len(obj.token) > 20 else obj.token
    token_short.short_description = _('Токен')
    
    def status_display(self, obj):
        """Статус токена с иконкой"""
        if obj.is_used:
            return format_html('<span style="color: gray;">✗ Использован</span>')
        elif obj.is_valid():
            return format_html('<span style="color: green;">✓ Действителен</span>')
        else:
            return format_html('<span style="color: red;">✗ Истек</span>')
    status_display.short_description = _('Статус')
    
    def expires_at_display(self, obj):
        """Форматирование даты истечения"""
        return obj.expires_at.strftime('%d.%m.%Y %H:%M')
    expires_at_display.short_description = _('Истекает')
    expires_at_display.admin_order_field = 'expires_at'
    
    def created_at_display(self, obj):
        """Форматирование даты создания"""
        return obj.created_at.strftime('%d.%m.%Y %H:%M')
    created_at_display.short_description = _('Создан')
    created_at_display.admin_order_field = 'created_at'
    
    
# Настройка заголовков админ-панели
admin.site.site_header = _('Order Service Администрирование')
admin.site.site_title = _('Order Service Admin')
admin.site.index_title = _('Управление системой')
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.template.loader import render_to_string
from datetime import timedelta
import uuid
import secrets
from .models import User, UserProfile, UserActivity, PasswordResetToken, Address


def register_user(email, password, first_name='', last_name='', 
                 role=User.Role.BUYER, phone='', company_name=''):
    """
    Регистрация нового пользователя.
    """
    # Проверяем уникальность email
    if User.objects.filter(email=email).exists():
        raise ValueError('Пользователь с таким email уже существует')
    
    # Создаем пользователя
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=role,
        phone=phone,
        company_name=company_name,
        email_verified=False  
    )
    
    # Создаем профиль пользователя
    UserProfile.objects.create(user=user)
    
    return user


def update_user_profile(user, **data):
    """
    Обновить профиль пользователя.
    """
    # Обновляем основные данные пользователя
    update_fields = ['first_name', 'last_name', 'phone', 'position']
    
    for field in update_fields:
        if field in data:
            setattr(user, field, data[field])
    
    user.save()
    
    # Обновляем профиль пользователя
    if hasattr(user, 'profile'):
        profile_fields = ['bio', 'language', 'timezone', 'currency']
        
        for field in profile_fields:
            if field in data:
                setattr(user.profile, field, data[field])
        
        user.profile.save()
    
    return user


def change_user_password(user, old_password, new_password):
    """
    Сменить пароль пользователя.
    """
    # Проверяем старый пароль
    if not user.check_password(old_password):
        raise ValueError('Неверный текущий пароль')
    
    # Устанавливаем новый пароль
    user.set_password(new_password)
    user.save()
    
    # Обновляем дату смены пароля в профиле
    if hasattr(user, 'profile'):
        user.profile.last_password_change = timezone.now()
        user.profile.save()
    
    return user


def reset_user_password(user, new_password):
    """
    Сбросить пароль пользователя.
    """
    # Устанавливаем новый пароль
    user.set_password(new_password)
    user.save()
    
    # Обновляем дату смены пароля в профиле
    if hasattr(user, 'profile'):
        user.profile.last_password_change = timezone.now()
        user.profile.save()
    
    return user


class EmailVerificationService:
    """
    Сервис для работы с подтверждением email.
    """
    
    @staticmethod
    def generate_verification_token():
        """
        Генерация уникального токена для подтверждения email.
        """
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def send_verification_email(user, request=None):
        """
        Отправка письма с подтверждением email.
        """
        # Генерируем токен
        token = EmailVerificationService.generate_verification_token()
        
        # Сохраняем токен и время отправки
        user.email_verification_token = token
        user.email_verification_sent_at = timezone.now()
        user.save()
        
        # Создаем ссылку для подтверждения
        if request:
            verification_url = request.build_absolute_uri(
                reverse('users:verify-email', kwargs={'token': token})
            )
        else:
            # Для фоновых задач или без request
            verification_url = f"{settings.FRONTEND_URL}/verify-email/{token}"
        
        # Контекст для шаблона
        context = {
            'user': user,
            'verification_url': verification_url,
            'site_name': getattr(settings, 'SITE_NAME', 'Order Service'),
            'valid_hours': 24,
            'year': timezone.now().year
        }
        
        try:
            # Отправляем письмо
            html_message = render_to_string('emails/email_verification.html', context)
            plain_message = render_to_string('emails/email_verification.txt', context)
            
            send_mail(
                subject='Подтверждение email адреса',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            # Логируем отправку
            log_user_activity(
                user=user,
                activity_type='email_verification_sent',
                description=f'Отправлено письмо подтверждения email на {user.email}',
                metadata={'token': token[:10] + '...'}
            )
            
            return True, 'Письмо отправлено успешно'
            
        except Exception as e:
            # Логируем ошибку
            log_user_activity(
                user=user,
                activity_type='email_verification_sent',
                description=f'Ошибка отправки письма: {str(e)}',
                metadata={'error': str(e)}
            )
            return False, f'Ошибка отправки письма: {str(e)}'
    
    @staticmethod
    def verify_email(token):
        """
        Подтверждение email по токену.
        """
        try:
            # Ищем пользователя с таким токеном
            user = User.objects.get(
                email_verification_token=token,
                email_verified=False
            )
            
            # Проверяем, не истек ли токен (24 часа)
            if user.is_email_verification_expired:
                return None, 'Токен подтверждения истек. Запросите повторную отправку.'
            
            # Подтверждаем email
            user.email_verified = True
            user.email_verification_token = None
            user.email_verification_sent_at = None
            user.is_verified = True  # Также отмечаем пользователя как верифицированного
            user.save()
            
            # Логируем подтверждение
            log_user_activity(
                user=user,
                activity_type='email_verification',
                description='Email успешно подтвержден',
                ip_address=None,
                user_agent=''
            )
            
            return user, 'Email успешно подтвержден!'
            
        except User.DoesNotExist:
            # Проверяем, может быть email уже подтвержден?
            try:
                user = User.objects.get(
                    email_verification_token=token,
                    email_verified=True
                )
                return user, 'Email уже был подтвержден ранее'
            except User.DoesNotExist:
                return None, 'Недействительный токен подтверждения'
    
    @staticmethod
    def resend_verification_email(user, request=None):
        """
        Повторная отправка письма подтверждения.
        """
        if user.email_verified:
            return False, 'Email уже подтвержден'
        
        # Проверяем, не отправляли ли мы письмо менее 5 минут назад
        if user.email_verification_sent_at:
            time_diff = timezone.now() - user.email_verification_sent_at
            if time_diff < timedelta(minutes=5):
                wait_minutes = 5 - time_diff.seconds // 60
                return False, f'Повторная отправка возможна через {wait_minutes} мин.'
        
        # Отправляем письмо
        success, message = EmailVerificationService.send_verification_email(user, request)
        return success, message
    
    @staticmethod
    def check_verification_status(user):
        """
        Проверка статуса подтверждения email.
        """
        return {
            'verified': user.email_verified,
            'token_exists': bool(user.email_verification_token),
            'expired': user.is_email_verification_expired if user.email_verification_token else None,
            'sent_at': user.email_verification_sent_at
        }


class AddressService:
    """
    Сервис для работы с адресами доставки.
    """
    
    @staticmethod
    def create_address(user, **data):
        """
        Создать новый адрес доставки.
        """
        # Проверяем обязательные поля
        required_fields = ['city', 'street', 'house', 'recipient_name', 'recipient_phone']
        for field in required_fields:
            if field not in data:
                raise ValueError(f'Обязательное поле: {field}')
        
        # Создаем адрес
        address = Address.objects.create(user=user, **data)
        
        # Логируем создание
        log_user_activity(
            user=user,
            activity_type='address_create',
            description=f'Добавлен адрес: {address.short_address}',
            metadata={'address_id': address.id, 'address_type': address.address_type}
        )
        
        return address
    
    @staticmethod
    def update_address(address, **data):
        """
        Обновить существующий адрес.
        """
        user = address.user
        
        # Обновляем поля
        for key, value in data.items():
            if hasattr(address, key):
                setattr(address, key, value)
        
        address.save()
        
        # Логируем обновление
        log_user_activity(
            user=user,
            activity_type='address_update',
            description=f'Обновлен адрес: {address.short_address}',
            metadata={'address_id': address.id}
        )
        
        return address
    
    @staticmethod
    def delete_address(address):
        """
        Удалить адрес доставки.
        """
        user = address.user
        address_info = address.short_address
        
        address.delete()
        
        # Логируем удаление
        log_user_activity(
            user=user,
            activity_type='address_delete',
            description=f'Удален адрес: {address_info}',
            metadata={'address_info': address_info}
        )
        
        return True
    
    @staticmethod
    def set_default_address(user, address_id):
        """
        Установить адрес по умолчанию.
        """
        try:
            address = Address.objects.get(id=address_id, user=user)
            address.is_default = True
            address.save()
            
            # Логируем установку
            log_user_activity(
                user=user,
                activity_type='address_set_default',
                description=f'Установлен адрес по умолчанию: {address.short_address}',
                metadata={'address_id': address.id}
            )
            
            return address
        except Address.DoesNotExist:
            raise ValueError('Адрес не найден')
    
    @staticmethod
    def get_user_addresses(user):
        """
        Получить все адреса пользователя.
        """
        return Address.objects.filter(user=user).order_by('-is_default', '-created_at')
    
    @staticmethod
    def get_default_address(user):
        """
        Получить адрес по умолчанию.
        """
        return Address.objects.filter(user=user, is_default=True).first()


def log_user_activity(user, activity_type, description='', 
                     ip_address=None, user_agent='', metadata=None):
    """
    Записать активность пользователя.
    """
    # Обновляем счетчик входов для типа 'login'
    if activity_type == 'login' and hasattr(user, 'profile'):
        user.profile.login_count += 1
        user.profile.last_login_ip = ip_address
        user.profile.save()
    
    # Создаем запись активности
    activity = UserActivity.objects.create(
        user=user,
        activity_type=activity_type,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )
    
    return activity


def create_password_reset_token(user):
    """
    Создать токен для сброса пароля.
    """
    # Удаляем старые неиспользованные токены
    PasswordResetToken.objects.filter(
        user=user,
        is_used=False,
        expires_at__lt=timezone.now()
    ).delete()
    
    # Создаем новый токен
    token = PasswordResetToken.objects.create(
        user=user,
        token=str(uuid.uuid4()),
        expires_at=timezone.now() + timedelta(hours=24)
    )
    
    return token


def send_password_reset_email(user, request=None):
    """
    Отправить письмо для сброса пароля.
    """
    # Создаем токен
    token_obj = create_password_reset_token(user)
    token = token_obj.token
    
    # Создаем ссылку для сброса
    if request:
        reset_url = request.build_absolute_uri(
            reverse('users:password-reset-confirm', kwargs={'token': token})
        )
    else:
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}"
    
    # Контекст для шаблона
    context = {
        'user': user,
        'reset_url': reset_url,
        'site_name': getattr(settings, 'SITE_NAME', 'Order Service'),
        'valid_hours': 24,
        'year': timezone.now().year
    }
    
    try:
        # Отправляем письмо
        html_message = render_to_string('emails/password_reset.html', context)
        plain_message = render_to_string('emails/password_reset.txt', context)
        
        send_mail(
            subject='Сброс пароля',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return True, 'Письмо для сброса пароля отправлено'
        
    except Exception as e:
        return False, f'Ошибка отправки письма: {str(e)}'


def verify_password_reset_token(token):
    """
    Проверить валидность токена сброса пароля.
    """
    try:
        token_obj = PasswordResetToken.objects.get(
            token=token,
            is_used=False,
            expires_at__gt=timezone.now()
        )
        return token_obj.user, token_obj
    except PasswordResetToken.DoesNotExist:
        return None, None


def use_password_reset_token(token, new_password):
    """
    Использовать токен и сменить пароль.
    """
    user, token_obj = verify_password_reset_token(token)
    
    if not user:
        raise ValueError('Недействительный или истекший токен')
    
    # Сбрасываем пароль
    user.set_password(new_password)
    user.save()
    
    # Обновляем дату смены пароля
    if hasattr(user, 'profile'):
        user.profile.last_password_change = timezone.now()
        user.profile.save()
    
    # Помечаем токен как использованный
    token_obj.is_used = True
    token_obj.save()
    
    return user


def get_user_statistics(user):
    """
    Получить статистику пользователя.
    """
    from apps.orders.models import Order
    
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Основная статистика
    total_activities = user.activities.count()
    login_count = user.profile.login_count if hasattr(user, 'profile') else 0
    
    # Статистика email подтверждения
    email_verified = user.email_verified
    
    # Статистика адресов
    total_addresses = user.addresses.count()
    default_address_exists = user.addresses.filter(is_default=True).exists()
    
    # Время с регистрации
    days_since_registration = (today - user.date_joined.date()).days
    
    # Время с последнего входа
    if user.last_login:
        days_since_last_login = (today - user.last_login.date()).days
    else:
        days_since_last_login = None
    
    # Статистика заказов
    orders = Order.objects.filter(created_by=user)
    total_orders = orders.count()
    total_order_amount = orders.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    avg_order_amount = orders.aggregate(
        avg=Avg('total_amount')
    )['avg'] or 0
    
    # Активность по периодам
    today_activities = user.activities.filter(
        created_at__date=today
    ).count()
    
    week_activities = user.activities.filter(
        created_at__date__gte=week_ago
    ).count()
    
    month_activities = user.activities.filter(
        created_at__date__gte=month_ago
    ).count()
    
    # Активность по типам
    activities_by_type = user.activities.values('activity_type').annotate(
        count=Count('id')
    )
    activity_type_dict = {
        item['activity_type']: item['count']
        for item in activities_by_type
    }
    
    # Активность по дням (последние 7 дней)
    from django.db.models.functions import TruncDate
    activity_by_day = user.activities.filter(
        created_at__date__gte=week_ago
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    day_list = [
        {
            'date': item['date'].strftime('%Y-%m-%d'),
            'count': item['count']
        }
        for item in activity_by_day
    ]
    
    return {
        'user_id': user.id,
        'user_email': user.email,
        'full_name': user.full_name,
        'role': user.role,
        'email_verified': email_verified,
        'total_addresses': total_addresses,
        'default_address_exists': default_address_exists,
        'total_activities': total_activities,
        'login_count': login_count,
        'days_since_registration': days_since_registration,
        'days_since_last_login': days_since_last_login,
        'total_orders': total_orders,
        'total_order_amount': float(total_order_amount),
        'avg_order_amount': float(avg_order_amount),
        'today_activities': today_activities,
        'week_activities': week_activities,
        'month_activities': month_activities,
        'activities_by_type': activity_type_dict,
        'activity_by_day': day_list
    }


def verify_user_email(user):
    """
    Подтвердить email пользователя.
    """
    user.email_verified = True
    user.is_verified = True
    user.save()
    
    # Логируем подтверждение email
    log_user_activity(
        user=user,
        activity_type='email_verification',
        description='Email подтвержден'
    )
    
    return user


def get_users_by_role(role):
    """
    Получить пользователей по роли.
    """
    return User.objects.filter(role=role, is_active=True)


def search_users(query, role=None, company_id=None, email_verified=None):
    """
    Поиск пользователей с фильтрацией.
    """
    users = User.objects.filter(is_active=True)
    
    if query:
        users = users.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(phone__icontains=query) |
            Q(company_name__icontains=query)
        )
    
    if role:
        users = users.filter(role=role)
    
    if company_id:
        users = users.filter(company_id=company_id)
    
    if email_verified is not None:
        users = users.filter(email_verified=email_verified)
    
    return users.order_by('-date_joined')


def get_users_needing_verification():
    """
    Получить пользователей, которым нужно повторно отправить подтверждение.
    """
    # Пользователи с неподтвержденным email, у которых токен истек
    expired_time = timezone.now() - timedelta(hours=24)
    return User.objects.filter(
        email_verified=False,
        email_verification_token__isnull=False,
        email_verification_sent_at__lt=expired_time
    ) 
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User, UserProfile, UserActivity, Address 
import re


class AddressSerializer(serializers.ModelSerializer):
    """
    Сериализатор для адреса доставки.
    Полный CRUD для адресов пользователя.
    """
    full_address = serializers.CharField(read_only=True)
    short_address = serializers.CharField(read_only=True)
    address_type_display = serializers.CharField(
        source='get_address_type_display', 
        read_only=True
    )
    
    class Meta:
        model = Address
        fields = [
            'id',
            'user',
            'address_type',
            'address_type_display',
            'city',
            'street',
            'house',
            'apartment',
            'entrance',
            'floor',
            'intercom',
            'recipient_name',
            'recipient_phone',
            'comment',
            'is_default',
            'full_address',
            'short_address',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def validate_recipient_phone(self, value):
        """Валидация телефона получателя"""
        if value:
            # Удаляем все нецифровые символы кроме +
            clean_phone = re.sub(r'[^\d+]', '', value)
            
            # Проверяем длину
            if len(clean_phone) < 10 or len(clean_phone) > 15:
                raise serializers.ValidationError(
                    'Номер телефона должен содержать от 10 до 15 цифр'
                )
        return value


class AddressCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания адреса доставки.
    """
    class Meta:
        model = Address
        fields = [
            'address_type',
            'city',
            'street',
            'house',
            'apartment',
            'entrance',
            'floor',
            'intercom',
            'recipient_name',
            'recipient_phone',
            'comment',
            'is_default'
        ]
    
    def validate(self, data):
        """Валидация обязательных полей при создании"""
        required_fields = ['city', 'street', 'house', 'recipient_name', 'recipient_phone']
        for field in required_fields:
            if field not in data:
                raise serializers.ValidationError({
                    field: 'Обязательное поле'
                })
        return data


class AddressUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления адреса доставки.
    Все поля опциональны.
    """
    class Meta:
        model = Address
        fields = [
            'address_type',
            'city',
            'street',
            'house',
            'apartment',
            'entrance',
            'floor',
            'intercom',
            'recipient_name',
            'recipient_phone',
            'comment',
            'is_default'
        ]
        extra_kwargs = {
            'address_type': {'required': False},
            'city': {'required': False},
            'street': {'required': False},
            'house': {'required': False},
            'apartment': {'required': False},
            'entrance': {'required': False},
            'floor': {'required': False},
            'intercom': {'required': False},
            'recipient_name': {'required': False},
            'recipient_phone': {'required': False},
            'comment': {'required': False},
            'is_default': {'required': False},
        }


class AddressListSerializer(serializers.ModelSerializer):
    """
    Оптимизированный сериализатор для списка адресов.
    """
    full_address = serializers.CharField(read_only=True)
    address_type_display = serializers.CharField(
        source='get_address_type_display', 
        read_only=True
    )
    
    class Meta:
        model = Address
        fields = [
            'id',
            'address_type',
            'address_type_display',
            'full_address',
            'recipient_name',
            'recipient_phone',
            'is_default',
            'created_at'
        ]


class AddressDetailSerializer(serializers.ModelSerializer):
    """
    Детальный сериализатор для адреса доставки.
    """
    full_address = serializers.CharField(read_only=True)
    short_address = serializers.CharField(read_only=True)
    address_type_display = serializers.CharField(
        source='get_address_type_display', 
        read_only=True
    )
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = Address
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class AddressDefaultSerializer(serializers.ModelSerializer):
    """
    Сериализатор для установки адреса по умолчанию.
    """
    class Meta:
        model = Address
        fields = ['id', 'is_default']
        read_only_fields = ['id']



class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для пользователя (краткий).
    """
    full_name = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'role_display',
            'phone',
            'company',
            'company_name',
            'position',
            'is_active',
            'is_verified',
            'date_joined',
            'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детальной информации о пользователе.
    Включает адреса доставки и профиль.
    """
    full_name = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    addresses = AddressListSerializer(many=True, read_only=True)
    addresses_count = serializers.IntegerField(source='addresses.count', read_only=True)
    default_address = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'role_display',
            'phone',
            'company',
            'company_name',
            'position',
            'is_active',
            'is_verified',
            'email_verified',
            'receive_notifications',
            'profile',
            'addresses',
            'addresses_count',
            'default_address',
            'date_joined',
            'last_login'
        ]
        read_only_fields = [
            'id', 'date_joined', 'last_login', 
            'email_verified', 'is_verified'
        ]
    
    def get_default_address(self, obj):
        """Получить адрес по умолчанию"""
        default_address = obj.addresses.filter(is_default=True).first()
        if default_address:
            return AddressListSerializer(default_address).data
        return None
    
    def get_profile(self, obj):
        """Получить профиль пользователя"""
        if hasattr(obj, 'profile'):
            from .serializers import UserProfileSerializer
            return UserProfileSerializer(obj.profile).data
        return None


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для профиля пользователя.
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id',
            'user',
            'user_email',
            'user_full_name',
            'avatar',
            'avatar_url',
            'bio',
            'notify_email',
            'notify_sms',
            'notify_push',
            'language',
            'timezone',
            'currency',
            'two_factor_auth',
            'login_count',
            'last_login_ip',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 
            'login_count', 'last_login_ip'
        ]
    
    def get_avatar_url(self, obj):
        """Получить URL аватара"""
        if obj.avatar:
            return obj.avatar.url
        return None


class RegisterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для регистрации пользователя.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        label='Подтверждение пароля'
    )
    
    class Meta:
        model = User
        fields = [
            'email',
            'first_name',
            'last_name',
            'password',
            'password2',
            'role',
            'phone',
            'company_name'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'role': {'required': False, 'default': User.Role.BUYER}
        }
    
    def validate(self, attrs):
        """Валидация данных регистрации"""
        # Проверка совпадения паролей
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                'password2': 'Пароли не совпадают'
            })
        
        # Проверка уникальности email
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({
                'email': 'Пользователь с таким email уже существует'
            })
        
        return attrs
    
    def validate_role(self, value):
        """Валидация роли"""
        # Новые пользователи не могут регистрироваться как администраторы
        if value in [User.Role.ADMIN, User.Role.NETWORK_ADMIN]:
            raise serializers.ValidationError('Невозможно зарегистрироваться с этой ролью')
        
        return value
    
    def create(self, validated_data):
        """Создание пользователя"""
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        return user


class UpdateUserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления пользователя.
    """
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'phone',
            'position',
            'receive_notifications'
        ]
    
    def validate_phone(self, value):
        """Валидация телефона"""
        if value:
            # Убираем все нецифровые символы кроме +
            clean_phone = re.sub(r'[^\d+]', '', value)
            
            # Проверяем длину
            if len(clean_phone) < 10:
                raise serializers.ValidationError('Номер телефона слишком короткий')
            
            return clean_phone
        
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Сериализатор для смены пароля.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password]
    )
    new_password2 = serializers.CharField(
        required=True,
        label='Подтверждение нового пароля'
    )
    
    def validate(self, attrs):
        """Валидация данных смены пароля"""
        # Проверка совпадения новых паролей
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                'new_password2': 'Новые пароли не совпадают'
            })
        
        # Проверка, что новый пароль отличается от старого
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                'new_password': 'Новый пароль должен отличаться от старого'
            })
        
        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    """
    Сериализатор для сброса пароля.
    """
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password]
    )
    new_password2 = serializers.CharField(
        required=True,
        label='Подтверждение нового пароля'
    )
    
    def validate(self, attrs):
        """Валидация данных сброса пароля"""
        # Проверка совпадения новых паролей
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                'new_password2': 'Пароли не совпадают'
            })
        
        return attrs


class UserActivitySerializer(serializers.ModelSerializer):
    """
    Сериализатор для активности пользователя.
    """
    user_email = serializers.CharField(source='user.email', read_only=True)
    activity_type_display = serializers.CharField(
        source='get_activity_type_display', 
        read_only=True
    )
    
    class Meta:
        model = UserActivity
        fields = [
            'id',
            'user',
            'user_email',
            'activity_type',
            'activity_type_display',
            'description',
            'ip_address',
            'user_agent',
            'metadata',
            'created_at'
        ]
        read_only_fields = '__all__'


class UserStatsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики пользователя.
    """
    user_id = serializers.IntegerField()
    user_email = serializers.EmailField()
    full_name = serializers.CharField()
    role = serializers.CharField()

    total_addresses = serializers.IntegerField(required=False, default=0)
    default_address_exists = serializers.BooleanField(required=False, default=False)
    email_verified = serializers.BooleanField(required=False, default=False)
    
    # Основная статистика
    total_activities = serializers.IntegerField()
    login_count = serializers.IntegerField()
    days_since_registration = serializers.IntegerField()
    days_since_last_login = serializers.IntegerField(allow_null=True)
    
    # Заказы
    total_orders = serializers.IntegerField()
    total_order_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # По периодам
    today_activities = serializers.IntegerField()
    week_activities = serializers.IntegerField()
    month_activities = serializers.IntegerField()
    
    # По типам активности
    activities_by_type = serializers.DictField(child=serializers.IntegerField())
    
    # Активность по дням
    activity_by_day = serializers.ListField(child=serializers.DictField())



class EmailVerificationSerializer(serializers.Serializer):
    """
    Сериализатор для подтверждения email.
    """
    token = serializers.CharField(required=True, help_text='Токен подтверждения')


class EmailVerificationResponseSerializer(serializers.Serializer):
    """
    Сериализатор ответа при подтверждении email.
    """
    success = serializers.BooleanField()
    message = serializers.CharField()
    email_verified = serializers.BooleanField()
    access = serializers.CharField(required=False)
    refresh = serializers.CharField(required=False)
    user = UserSerializer(required=False)


class ResendVerificationSerializer(serializers.Serializer):
    """
    Сериализатор для повторной отправки подтверждения.
    """
    email = serializers.EmailField(required=False, help_text='Email для повторной отправки')
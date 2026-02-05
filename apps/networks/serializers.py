from rest_framework import serializers
from django.db.models import Count, Sum, Avg
from django.utils import timezone

from .models import RetailNetwork, Store, StoreAssignment, NetworkSettings
from apps.users.serializers import UserShortSerializer


class RetailNetworkSerializer(serializers.ModelSerializer):
    """
    Сериализатор для розничной сети.
    """
    stores_count = serializers.IntegerField(read_only=True)
    employees_count = serializers.IntegerField(read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    monthly_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    budget_utilization = serializers.FloatField(read_only=True)
    
    class Meta:
        model = RetailNetwork
        fields = [
            'id',
            'name',
            'legal_name',
            'tax_id',
            'contact_email',
            'contact_phone',
            'monthly_budget',
            'is_active',
            'is_verified',
            'stores_count',
            'employees_count',
            'created_by_name',
            'monthly_spent',
            'budget_utilization',
            'created_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'stores_count', 'employees_count',
            'monthly_spent', 'budget_utilization'
        ]


class RetailNetworkDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детальной информации о сети.
    """
    stores_count = serializers.IntegerField(read_only=True)
    employees_count = serializers.IntegerField(read_only=True)
    total_orders = serializers.IntegerField(read_only=True)
    monthly_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    budget_utilization = serializers.FloatField(read_only=True)
    created_by = UserShortSerializer(read_only=True)
    administrators = UserShortSerializer(many=True, read_only=True)
    
    class Meta:
        model = RetailNetwork
        fields = [
            'id',
            'name',
            'legal_name',
            'tax_id',
            'legal_address',
            'contact_email',
            'contact_phone',
            'website',
            'description',
            'monthly_budget',
            'min_order_amount',
            'is_active',
            'is_verified',
            'stores_count',
            'employees_count',
            'total_orders',
            'monthly_spent',
            'budget_utilization',
            'created_by',
            'administrators',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'stores_count',
            'employees_count', 'total_orders', 'monthly_spent',
            'budget_utilization'
        ]


class CreateNetworkSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания сети.
    """
    class Meta:
        model = RetailNetwork
        fields = [
            'name',
            'legal_name',
            'tax_id',
            'legal_address',
            'contact_email',
            'contact_phone',
            'website',
            'description',
            'monthly_budget',
            'min_order_amount'
        ]
    
    def validate_tax_id(self, value):
        """Валидация ИНН"""
        if RetailNetwork.objects.filter(tax_id=value).exists():
            raise serializers.ValidationError('Сеть с таким ИНН уже существует')
        return value
    
    def validate_monthly_budget(self, value):
        """Валидация бюджета"""
        if value < 0:
            raise serializers.ValidationError('Бюджет не может быть отрицательным')
        return value


class UpdateNetworkSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления сети.
    """
    class Meta:
        model = RetailNetwork
        fields = [
            'name',
            'legal_name',
            'legal_address',
            'contact_email',
            'contact_phone',
            'website',
            'description',
            'monthly_budget',
            'min_order_amount',
            'is_active',
            'is_verified'
        ]
    
    def validate_monthly_budget(self, value):
        """Валидация бюджета"""
        if value < 0:
            raise serializers.ValidationError('Бюджет не может быть отрицательным')
        return value


class StoreSerializer(serializers.ModelSerializer):
    """
    Сериализатор для магазина.
    """
    network_name = serializers.CharField(source='network.name', read_only=True)
    full_address = serializers.CharField(read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    monthly_spent = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    budget_utilization = serializers.FloatField(read_only=True)
    total_orders = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Store
        fields = [
            'id',
            'name',
            'store_code',
            'network',
            'network_name',
            'store_type',
            'status',
            'full_address',
            'city',
            'region',
            'phone',
            'monthly_budget',
            'manager',
            'manager_name',
            'monthly_spent',
            'budget_utilization',
            'total_orders',
            'opened_at'
        ]
        read_only_fields = [
            'id', 'network_name', 'full_address', 'manager_name',
            'monthly_spent', 'budget_utilization', 'total_orders'
        ]


class StoreDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детальной информации о магазине.
    """
    network_name = serializers.CharField(source='network.name', read_only=True)
    full_address = serializers.CharField(read_only=True)
    coordinates = serializers.SerializerMethodField()
    manager = UserShortSerializer(read_only=True)
    monthly_spent = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    budget_utilization = serializers.FloatField(read_only=True)
    total_orders = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Store
        fields = [
            'id',
            'name',
            'store_code',
            'network',
            'network_name',
            'store_type',
            'status',
            'address',
            'city',
            'region',
            'postal_code',
            'full_address',
            'latitude',
            'longitude',
            'coordinates',
            'phone',
            'email',
            'area',
            'opening_hours',
            'monthly_budget',
            'manager',
            'staff_count',
            'average_daily_traffic',
            'average_check',
            'monthly_spent',
            'budget_utilization',
            'total_orders',
            'opened_at',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id', 'network_name', 'full_address', 'coordinates',
            'monthly_spent', 'budget_utilization', 'total_orders',
            'created_at', 'updated_at'
        ]
    
    def get_coordinates(self, obj):
        """Получить координаты в формате JSON"""
        if obj.latitude and obj.longitude:
            return {'lat': float(obj.latitude), 'lng': float(obj.longitude)}
        return None


class CreateStoreSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания магазина.
    """
    class Meta:
        model = Store
        fields = [
            'name',
            'store_code',
            'network',
            'store_type',
            'address',
            'city',
            'region',
            'postal_code',
            'latitude',
            'longitude',
            'phone',
            'email',
            'area',
            'opening_hours',
            'monthly_budget',
            'manager',
            'staff_count',
            'average_daily_traffic',
            'average_check',
            'opened_at'
        ]
    
    def validate_store_code(self, value):
        """Валидация кода магазина"""
        if Store.objects.filter(store_code=value).exists():
            raise serializers.ValidationError('Магазин с таким кодом уже существует')
        return value
    
    def validate(self, data):
        """Общая валидация"""
        network = data.get('network')
        
        # Проверяем, что код магазина уникален в рамках сети
        store_code = data.get('store_code')
        if store_code and network:
            if Store.objects.filter(network=network, store_code=store_code).exists():
                raise serializers.ValidationError({
                    'store_code': 'Магазин с таким кодом уже существует в этой сети'
                })
        
        return data


class UpdateStoreSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления магазина.
    """
    class Meta:
        model = Store
        fields = [
            'name',
            'store_type',
            'status',
            'address',
            'city',
            'region',
            'postal_code',
            'latitude',
            'longitude',
            'phone',
            'email',
            'area',
            'opening_hours',
            'monthly_budget',
            'manager',
            'staff_count',
            'average_daily_traffic',
            'average_check',
            'opened_at'
        ]
    
    def validate_monthly_budget(self, value):
        """Валидация бюджета"""
        if value < 0:
            raise serializers.ValidationError('Бюджет не может быть отрицательным')
        return value


class StoreAssignmentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для назначения на магазин.
    """
    user = UserShortSerializer(read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    
    class Meta:
        model = StoreAssignment
        fields = [
            'id',
            'user',
            'store',
            'store_name',
            'role',
            'is_primary',
            'assigned_by',
            'assigned_by_name',
            'assigned_at'
        ]
        read_only_fields = ['id', 'assigned_at']


class NetworkSettingsSerializer(serializers.ModelSerializer):
    """
    Сериализатор для настроек сети.
    """
    class Meta:
        model = NetworkSettings
        fields = [
            'require_approval',
            'approval_threshold',
            'max_order_amount',
            'notify_on_new_order',
            'notify_on_order_status_change',
            'notify_on_budget_threshold',
            'budget_threshold_percent',
            'allow_api_access',
            'api_key',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_approval_threshold(self, value):
        """Валидация порога подтверждения"""
        if value < 0:
            raise serializers.ValidationError('Порог не может быть отрицательным')
        return value
    
    def validate_max_order_amount(self, value):
        """Валидация максимальной суммы заказа"""
        if value < 0:
            raise serializers.ValidationError('Максимальная сумма не может быть отрицательной')
        return value
    
    def validate_budget_threshold_percent(self, value):
        """Валидация порога бюджета"""
        if value < 0 or value > 100:
            raise serializers.ValidationError('Порог должен быть в диапазоне 0-100%')
        return value


class NetworkStatsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики сети.
    """
    network_id = serializers.IntegerField()
    network_name = serializers.CharField()
    
    # Основная статистика
    stores_count = serializers.IntegerField()
    employees_count = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    # Бюджет
    monthly_budget = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    budget_utilization = serializers.FloatField()
    
    # По периодам
    today_orders = serializers.IntegerField()
    week_orders = serializers.IntegerField()
    month_orders = serializers.IntegerField()
    
    today_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    week_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    month_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # По статусам
    orders_by_status = serializers.DictField(child=serializers.IntegerField())
    
    # По городам
    stores_by_city = serializers.ListField(child=serializers.DictField())
    
    # Топ магазинов
    top_stores = serializers.ListField(child=serializers.DictField())


class StoreStatsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики магазина.
    """
    store_id = serializers.IntegerField()
    store_name = serializers.CharField()
    network_name = serializers.CharField()
    
    # Основная статистика
    total_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    avg_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Бюджет
    monthly_budget = serializers.DecimalField(max_digits=10, decimal_places=2)
    monthly_spent = serializers.DecimalField(max_digits=10, decimal_places=2)
    budget_utilization = serializers.FloatField()
    
    # По периодам
    today_orders = serializers.IntegerField()
    week_orders = serializers.IntegerField()
    month_orders = serializers.IntegerField()
    
    today_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    week_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    month_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # По статусам
    orders_by_status = serializers.DictField(child=serializers.IntegerField())
    
    # Топ товаров
    top_products = serializers.ListField(child=serializers.DictField())
    
    # Активность
    last_order_date = serializers.DateField()
    days_since_last_order = serializers.IntegerField()

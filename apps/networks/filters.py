from django_filters import rest_framework as filters
from .models import RetailNetwork, Store


class RetailNetworkFilter(filters.FilterSet):
    """
    Фильтры для розничных сетей.
    """
    is_active = filters.BooleanFilter(field_name='is_active')
    is_verified = filters.BooleanFilter(field_name='is_verified')
    min_stores = filters.NumberFilter(
        method='filter_min_stores',
        label='Минимальное количество магазинов'
    )
    min_budget = filters.NumberFilter(
        field_name='monthly_budget',
        lookup_expr='gte'
    )
    max_budget = filters.NumberFilter(
        field_name='monthly_budget',
        lookup_expr='lte'
    )
    created_after = filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    
    class Meta:
        model = RetailNetwork
        fields = [
            'is_active',
            'is_verified',
            'min_stores',
            'min_budget',
            'max_budget',
            'created_after',
            'created_before'
        ]
    
    def filter_min_stores(self, queryset, name, value):
        """
        Фильтр по минимальному количеству магазинов.
        """
        return queryset.annotate(
            store_count=filters.Count('stores')
        ).filter(store_count__gte=value)


class StoreFilter(filters.FilterSet):
    """
    Фильтры для магазинов.
    """
    network = filters.NumberFilter(field_name='network_id')
    status = filters.ChoiceFilter(
        choices=Store.StoreStatus.choices
    )
    store_type = filters.ChoiceFilter(
        choices=Store.StoreType.choices
    )
    city = filters.CharFilter(
        field_name='city',
        lookup_expr='icontains'
    )
    region = filters.CharFilter(
        field_name='region',
        lookup_expr='icontains'
    )
    has_manager = filters.BooleanFilter(
        method='filter_has_manager',
        label='Имеет менеджера'
    )
    min_budget = filters.NumberFilter(
        field_name='monthly_budget',
        lookup_expr='gte'
    )
    max_budget = filters.NumberFilter(
        field_name='monthly_budget',
        lookup_expr='lte'
    )
    opened_after = filters.DateFilter(
        field_name='opened_at',
        lookup_expr='gte'
    )
    opened_before = filters.DateFilter(
        field_name='opened_at',
        lookup_expr='lte'
    )
    
    class Meta:
        model = Store
        fields = [
            'network',
            'status',
            'store_type',
            'city',
            'region',
            'has_manager',
            'min_budget',
            'max_budget',
            'opened_after',
            'opened_before'
        ]
    
    def filter_has_manager(self, queryset, name, value):
        """
        Фильтр по наличию менеджера.
        """
        if value:
            return queryset.filter(manager__isnull=False)
        return queryset.filter(manager__isnull=True)
from django_filters import rest_framework as filters
from apps.users.models import User


class SupplierFilter(filters.FilterSet):
    """
    Фильтры для поставщиков.
    """
    is_active = filters.BooleanFilter(field_name='is_active')
    company_name = filters.CharFilter(
        field_name='company_name',
        lookup_expr='icontains'
    )
    email = filters.CharFilter(
        field_name='email',
        lookup_expr='icontains'
    )
    date_joined_from = filters.DateFilter(
        field_name='date_joined',
        lookup_expr='gte'
    )
    date_joined_to = filters.DateFilter(
        field_name='date_joined',
        lookup_expr='lte'
    )
    min_products = filters.NumberFilter(
        method='filter_min_products',
        label='Минимальное количество товаров'
    )
    has_orders = filters.BooleanFilter(
        method='filter_has_orders',
        label='Имеет заказы'
    )
    
    class Meta:
        model = User
        fields = [
            'is_active',
            'company_name',
            'email',
            'date_joined_from',
            'date_joined_to'
        ]
    
    def filter_min_products(self, queryset, name, value):
        """
        Фильтр по минимальному количеству товаров.
        """
        from apps.products.models import Product
        
        # Находим поставщиков с указанным минимальным количеством товаров
        supplier_ids = Product.objects.values('supplier').annotate(
            count=Count('id')
        ).filter(count__gte=value).values_list('supplier', flat=True)
        
        return queryset.filter(id__in=supplier_ids)
    
    def filter_has_orders(self, queryset, name, value):
        """
        Фильтр по наличию заказов.
        """
        from apps.orders.models import Order
        
        if value:
            # Поставщики с заказами
            supplier_ids = Order.objects.filter(
                items__product__supplier__isnull=False
            ).values_list('items__product__supplier', flat=True).distinct()
        else:
            # Поставщики без заказов
            supplier_ids = Order.objects.filter(
                items__product__supplier__isnull=False
            ).values_list('items__product__supplier', flat=True).distinct()
            supplier_ids = User.objects.filter(
                role='supplier'
            ).exclude(id__in=supplier_ids).values_list('id', flat=True)
        
        return queryset.filter(id__in=supplier_ids)

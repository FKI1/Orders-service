from django_filters import rest_framework as filters
from .models import Order, Payment


class OrderFilter(filters.FilterSet):
    """
    Фильтры для заказов.
    """
    status = filters.ChoiceFilter(
        choices=Order.Status.choices
    )
    
    payment_status = filters.ChoiceFilter(
        choices=Order.PaymentStatus.choices
    )
    
    store = filters.NumberFilter(field_name='store_id')
    
    created_by = filters.NumberFilter(field_name='created_by_id')
    
    min_amount = filters.NumberFilter(
        field_name='total_amount',
        lookup_expr='gte'
    )
    
    max_amount = filters.NumberFilter(
        field_name='total_amount',
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
    
    delivery_after = filters.DateFilter(
        field_name='required_delivery_date',
        lookup_expr='gte'
    )
    
    delivery_before = filters.DateFilter(
        field_name='required_delivery_date',
        lookup_expr='lte'
    )
    
    has_payments = filters.BooleanFilter(
        method='filter_has_payments',
        label='Имеет платежи'
    )
    
    is_paid = filters.BooleanFilter(
        method='filter_is_paid',
        label='Оплачен полностью'
    )
    
    class Meta:
        model = Order
        fields = [
            'status',
            'payment_status',
            'store',
            'created_by',
            'min_amount',
            'max_amount',
            'created_after',
            'created_before',
            'delivery_after',
            'delivery_before',
            'has_payments',
            'is_paid'
        ]
    
    def filter_has_payments(self, queryset, name, value):
        """
        Фильтр по наличию платежей.
        """
        if value:
            return queryset.filter(payments__isnull=False).distinct()
        return queryset.filter(payments__isnull=True)
    
    def filter_is_paid(self, queryset, name, value):
        """
        Фильтр по полной оплате.
        """
        if value:
            return queryset.filter(payment_status='paid')
        return queryset.exclude(payment_status='paid')


class PaymentFilter(filters.FilterSet):
    """
    Фильтры для платежей.
    """
    status = filters.ChoiceFilter(
        choices=Payment.PaymentStatus.choices
    )
    
    payment_method = filters.ChoiceFilter(
        choices=Payment.PaymentMethod.choices
    )
    
    order = filters.NumberFilter(field_name='order_id')
    
    min_amount = filters.NumberFilter(
        field_name='amount',
        lookup_expr='gte'
    )
    
    max_amount = filters.NumberFilter(
        field_name='amount',
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
        model = Payment
        fields = [
            'status',
            'payment_method',
            'order',
            'min_amount',
            'max_amount',
            'created_after',
            'created_before'
        ]

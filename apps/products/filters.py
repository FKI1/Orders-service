from django_filters import rest_framework as filters
from .models import Product, Category


class ProductFilter(filters.FilterSet):
    """
    Фильтры для товаров.
    """
    category = filters.NumberFilter(field_name='category_id')
    supplier = filters.NumberFilter(field_name='supplier_id')
    status = filters.ChoiceFilter(choices=Product.ProductStatus.choices)
    in_stock = filters.BooleanFilter(field_name='in_stock')
    
    min_price = filters.NumberFilter(
        field_name='price',
        lookup_expr='gte'
    )
    
    max_price = filters.NumberFilter(
        field_name='price',
        lookup_expr='lte'
    )
    
    min_stock = filters.NumberFilter(
        field_name='stock_quantity',
        lookup_expr='gte'
    )
    
    max_stock = filters.NumberFilter(
        field_name='stock_quantity',
        lookup_expr='lte'
    )
    
    min_rating = filters.NumberFilter(
        field_name='rating',
        lookup_expr='gte'
    )
    
    has_discount = filters.BooleanFilter(
        method='filter_has_discount',
        label='Есть скидка'
    )
    
    low_stock = filters.BooleanFilter(
        method='filter_low_stock',
        label='Мало на складе'
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
        model = Product
        fields = [
            'category',
            'supplier',
            'status',
            'in_stock',
            'min_price',
            'max_price',
            'min_stock',
            'max_stock',
            'min_rating',
            'has_discount',
            'low_stock',
            'created_after',
            'created_before'
        ]
    
    def filter_has_discount(self, queryset, name, value):
        """
        Фильтр по наличию скидки.
        """
        if value:
            return queryset.filter(old_price__gt=F('price'))
        return queryset
    
    def filter_low_stock(self, queryset, name, value):
        """
        Фильтр по низкому остатку.
        """
        if value:
            return queryset.filter(
                stock_quantity__lte=F('min_stock_level'),
                in_stock=True
            )
        return queryset


class CategoryFilter(filters.FilterSet):
    """
    Фильтры для категорий.
    """
    parent = filters.NumberFilter(field_name='parent_id')
    is_active = filters.BooleanFilter(field_name='is_active')
    
    class Meta:
        model = Category
        fields = ['parent', 'is_active']

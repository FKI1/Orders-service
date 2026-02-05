from django_filters import rest_framework as filters
from .models import User


class UserFilter(filters.FilterSet):
    """
    Фильтры для пользователей.
    """
    role = filters.ChoiceFilter(
        choices=User.Role.choices
    )
    
    is_active = filters.BooleanFilter(field_name='is_active')
    is_verified = filters.BooleanFilter(field_name='is_verified')
    email_verified = filters.BooleanFilter(field_name='email_verified')
    
    company = filters.NumberFilter(field_name='company_id')
    
    created_after = filters.DateFilter(
        field_name='date_joined',
        lookup_expr='gte'
    )
    
    created_before = filters.DateFilter(
        field_name='date_joined',
        lookup_expr='lte'
    )
    
    last_login_after = filters.DateFilter(
        field_name='last_login',
        lookup_expr='gte'
    )
    
    last_login_before = filters.DateFilter(
        field_name='last_login',
        lookup_expr='lte'
    )
    
    has_company = filters.BooleanFilter(
        method='filter_has_company',
        label='Имеет компанию'
    )
    
    class Meta:
        model = User
        fields = [
            'role',
            'is_active',
            'is_verified',
            'email_verified',
            'company',
            'created_after',
            'created_before',
            'last_login_after',
            'last_login_before',
            'has_company'
        ]
    
    def filter_has_company(self, queryset, name, value):
        """
        Фильтр по наличию компании.
        """
        if value:
            return queryset.filter(company__isnull=False)
        return queryset.filter(company__isnull=True)

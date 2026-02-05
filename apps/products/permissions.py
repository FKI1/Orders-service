from rest_framework import permissions


class CanViewProduct(permissions.BasePermission):
    """
    Разрешение на просмотр товаров.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated


class CanCreateProduct(permissions.BasePermission):
    """
    Разрешение на создание товаров.
    """
    def has_permission(self, request, view):
        user = request.user
        
        if not user.is_authenticated:
            return False
        
        # Администраторы и поставщики могут создавать товары
        return user.role in ['admin', 'supplier']


class CanUpdateProduct(permissions.BasePermission):
    """
    Разрешение на обновление товаров.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Администраторы могут обновлять все
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Поставщик может обновлять только свои товары
        if user.role == 'supplier':
            return obj.supplier == user
        
        return False


class CanDeleteProduct(permissions.BasePermission):
    """
    Разрешение на удаление товаров.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Администраторы могут удалять все
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Поставщик может удалять только свои товары
        if user.role == 'supplier':
            return obj.supplier == user
        
        return False


class IsSupplierOrAdmin(permissions.BasePermission):
    """
    Разрешение для поставщиков или администраторов.
    """
    def has_permission(self, request, view):
        user = request.user
        
        if not user.is_authenticated:
            return False
        
        return user.role in ['admin', 'supplier']

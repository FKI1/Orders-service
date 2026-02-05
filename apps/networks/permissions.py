from rest_framework import permissions


class IsNetworkAdmin(permissions.BasePermission):
    """
    Разрешение для администраторов сети.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'network_admin'
    
    def has_object_permission(self, request, view, obj):
        # Проверяем, является ли пользователь администратором этой сети
        if hasattr(obj, 'administrators'):
            return obj.administrators.filter(id=request.user.id).exists()
        elif hasattr(obj, 'network'):
            return obj.network.administrators.filter(id=request.user.id).exists()
        return False


class IsNetworkMember(permissions.BasePermission):
    """
    Разрешение для сотрудников сети.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [
            'network_admin', 'store_manager', 'buyer'
        ]
    
    def has_object_permission(self, request, view, obj):
        # Проверяем, является ли пользователь сотрудником сети
        user = request.user
        
        if user.is_superuser or user.role == 'admin':
            return True
        
        if hasattr(obj, 'employees'):
            return obj.employees.filter(id=user.id).exists()
        elif hasattr(obj, 'network'):
            return obj.network.employees.filter(id=user.id).exists()
        return False


class IsStoreManager(permissions.BasePermission):
    """
    Разрешение для менеджеров магазинов.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'store_manager'
    
    def has_object_permission(self, request, view, obj):
        # Проверяем, является ли пользователь менеджером этого магазина
        user = request.user
        
        if hasattr(obj, 'manager'):
            return obj.manager == user
        elif hasattr(obj, 'store'):
            return obj.store.manager == user
        return False


class CanManageNetwork(permissions.BasePermission):
    """
    Разрешение на управление сетью.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or 
            request.user.role in ['admin', 'network_admin']
        )
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if user.is_superuser or user.role == 'admin':
            return True
        
        if user.role == 'network_admin':
            # Проверяем, является ли пользователь администратором этой сети
            if hasattr(obj, 'administrators'):
                return obj.administrators.filter(id=user.id).exists()
            elif hasattr(obj, 'network'):
                return obj.network.administrators.filter(id=user.id).exists()
        
        return False


class CanManageStore(permissions.BasePermission):
    """
    Разрешение на управление магазином.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or 
            request.user.role in ['admin', 'network_admin', 'store_manager']
        )
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Администратор сети может управлять магазинами своей сети
        if user.role == 'network_admin':
            if hasattr(obj, 'network'):
                return obj.network.administrators.filter(id=user.id).exists()
        
        # Менеджер магазина может управлять своим магазином
        if user.role == 'store_manager':
            if hasattr(obj, 'manager'):
                return obj.manager == user
            elif hasattr(obj, 'store'):
                return obj.store.manager == user
        
        return False

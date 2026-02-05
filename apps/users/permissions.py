from rest_framework import permissions


class CanViewUser(permissions.BasePermission):
    """
    Разрешение на просмотр пользователей.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Администраторы видят всех
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Пользователь видит себя
        if obj == user:
            return True
        
        # Администратор сети видит сотрудников своей сети
        if user.role == 'network_admin' and user.company:
            return obj.company == user.company
        
        # Менеджер магазина видит себя и сотрудников своего магазина
        if user.role == 'store_manager':
            # Здесь можно добавить логику для менеджеров магазинов
            pass
        
        return False


class CanUpdateUser(permissions.BasePermission):
    """
    Разрешение на обновление пользователей.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Администраторы могут обновлять всех
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Пользователь может обновлять себя
        if obj == user:
            return True
        
        # Администратор сети может обновлять сотрудников своей сети
        if user.role == 'network_admin' and user.company:
            return obj.company == user.company
        
        return False


class CanDeleteUser(permissions.BasePermission):
    """
    Разрешение на удаление пользователей.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Администраторы могут удалять всех (кроме себя)
        if (user.is_superuser or user.role == 'admin') and obj != user:
            return True
        
        return False


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Разрешение для владельца или администратора.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Администраторы имеют полный доступ
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Владелец объекта имеет доступ
        if hasattr(obj, 'user'):
            return obj.user == user
        
        return False


class IsAdminOrSelf(permissions.BasePermission):
    """
    Разрешение для администратора или самого пользователя.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Администраторы имеют полный доступ
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Пользователь имеет доступ к своим данным
        return obj == user


class IsSupplierOrAdmin(permissions.BasePermission):
    """
    Разрешение для поставщиков или администраторов.
    """
    def has_permission(self, request, view):
        user = request.user
        
        if not user.is_authenticated:
            return False
        
        return user.role in ['admin', 'supplier']


class IsNetworkAdminOrAdmin(permissions.BasePermission):
    """
    Разрешение для администраторов сетей или глобальных администраторов.
    """
    def has_permission(self, request, view):
        user = request.user
        
        if not user.is_authenticated:
            return False
        
        return user.role in ['admin', 'network_admin']

from rest_framework import permissions


class CanViewOrder(permissions.BasePermission):
    """
    Разрешение на просмотр заказа.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Администраторы видят все
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Создатель заказа видит свой заказ
        if obj.created_by == user:
            return True
        
        # Администратор сети видит заказы своей сети
        if user.role == 'network_admin':
            return obj.store.network.administrators.filter(id=user.id).exists()
        
        # Менеджер магазина видит заказы своего магазина
        if user.role == 'store_manager':
            return obj.store.manager == user
        
        # Сотрудник магазина видит заказы своего магазина
        if user.role == 'buyer':
            from apps.networks.models import StoreAssignment
            return StoreAssignment.objects.filter(
                user=user,
                store=obj.store
            ).exists()
        
        return False


class CanCreateOrder(permissions.BasePermission):
    """
    Разрешение на создание заказа.
    """
    def has_permission(self, request, view):
        user = request.user
        
        if not user.is_authenticated:
            return False
        
        # Администраторы и закупщики могут создавать заказы
        return user.role in ['admin', 'buyer', 'store_manager']


class CanUpdateOrder(permissions.BasePermission):
    """
    Разрешение на обновление заказа.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Администраторы могут обновлять все
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Создатель может обновлять только черновики
        if obj.created_by == user:
            return obj.status == 'draft'
        
        # Администратор сети может обновлять заказы своей сети
        if user.role == 'network_admin':
            if obj.store.network.administrators.filter(id=user.id).exists():
                # Не может обновлять доставленные или отмененные заказы
                return obj.status not in ['delivered', 'cancelled', 'rejected']
        
        return False


class CanDeleteOrder(permissions.BasePermission):
    """
    Разрешение на удаление заказа.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Администраторы могут удалять все
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Создатель может удалять только черновики
        if obj.created_by == user:
            return obj.status == 'draft'
        
        return False


class CanApproveOrder(permissions.BasePermission):
    """
    Разрешение на подтверждение заказа.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Администраторы могут подтверждать все
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Администратор сети может подтверждать заказы своей сети
        if user.role == 'network_admin':
            return (
                obj.status == 'pending' and
                obj.store.network.administrators.filter(id=user.id).exists()
            )
        
        return False


class CanCancelOrder(permissions.BasePermission):
    """
    Разрешение на отмену заказа.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Администраторы могут отменять все
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Создатель может отменять свои заказы
        if obj.created_by == user:
            return obj.can_be_cancelled
        
        # Администратор сети может отменять заказы своей сети
        if user.role == 'network_admin':
            return (
                obj.can_be_cancelled and
                obj.store.network.administrators.filter(id=user.id).exists()
            )
        
        # Менеджер магазина может отменять заказы своего магазина
        if user.role == 'store_manager':
            return (
                obj.can_be_cancelled and
                obj.store.manager == user
            )
        
        return False

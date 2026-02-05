from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, Avg, F
from django.utils import timezone
from datetime import timedelta

from .models import RetailNetwork, Store, StoreAssignment, NetworkSettings
from .serializers import (
    RetailNetworkSerializer,
    RetailNetworkDetailSerializer,
    StoreSerializer,
    StoreDetailSerializer,
    StoreAssignmentSerializer,
    NetworkSettingsSerializer,
    CreateNetworkSerializer,
    UpdateNetworkSerializer,
    CreateStoreSerializer,
    UpdateStoreSerializer,
    NetworkStatsSerializer,
    StoreStatsSerializer
)
from .permissions import (
    IsNetworkAdmin,
    IsNetworkMember,
    IsStoreManager,
    CanManageNetwork,
    CanManageStore
)
from .filters import RetailNetworkFilter, StoreFilter
from .services import (
    calculate_network_stats,
    calculate_store_stats,
    get_network_dashboard,
    get_store_dashboard,
    assign_user_to_store,
    remove_user_from_store,
    update_network_budget,
    update_store_budget
)


class RetailNetworkViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления розничными сетями.
    """
    queryset = RetailNetwork.objects.all().select_related('created_by').prefetch_related('stores')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = RetailNetworkFilter
    search_fields = ['name', 'legal_name', 'tax_id', 'contact_email']
    ordering_fields = ['name', 'created_at', 'monthly_budget']
    
    def get_permissions(self):
        """
        Динамические разрешения в зависимости от действия.
        """
        if self.action in ['create']:
            self.permission_classes = [IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsAdminUser | CanManageNetwork]
        return super().get_permissions()
    
    def get_queryset(self):
        """
        Фильтрация сетей в зависимости от роли пользователя.
        """
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            return self.queryset.all()
        
        # Сети, где пользователь является администратором
        if user.role == 'network_admin':
            return self.queryset.filter(
                Q(administrators=user) | Q(created_by=user)
            ).distinct()
        
        # Сети, где пользователь является менеджером магазина
        if user.role == 'store_manager':
            return self.queryset.filter(
                stores__manager=user
            ).distinct()
        
        # Сети, где пользователь является сотрудником
        if user.role == 'buyer':
            return self.queryset.filter(
                Q(employees=user) |
                Q(stores__assignments__user=user)
            ).distinct()
        
        return RetailNetwork.objects.none()
    
    def get_serializer_class(self):
        """
        Выбор сериализатора в зависимости от действия.
        """
        if self.action == 'create':
            return CreateNetworkSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateNetworkSerializer
        elif self.action == 'retrieve':
            return RetailNetworkDetailSerializer
        return RetailNetworkSerializer
    
    def perform_create(self, serializer):
        """
        Создание сети с указанием создателя.
        """
        network = serializer.save(created_by=self.request.user)
        
        # Автоматически добавляем создателя как администратора
        if self.request.user.role == 'network_admin':
            network.administrators.add(self.request.user)
        
        # Создаем настройки по умолчанию
        NetworkSettings.objects.create(network=network)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        GET /api/networks/{id}/stats/
        Статистика сети.
        """
        network = self.get_object()
        stats = calculate_network_stats(network)
        serializer = NetworkStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        """
        GET /api/networks/{id}/dashboard/
        Дашборд сети.
        """
        network = self.get_object()
        dashboard_data = get_network_dashboard(network)
        return Response(dashboard_data)
    
    @action(detail=True, methods=['get'])
    def stores(self, request, pk=None):
        """
        GET /api/networks/{id}/stores/
        Магазины сети.
        """
        network = self.get_object()
        stores = network.stores.all()
        
        # Фильтрация магазинов
        status_filter = request.query_params.get('status')
        city_filter = request.query_params.get('city')
        
        if status_filter:
            stores = stores.filter(status=status_filter)
        if city_filter:
            stores = stores.filter(city=city_filter)
        
        # Пагинация
        page = self.paginate_queryset(stores)
        if page is not None:
            serializer = StoreSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = StoreSerializer(stores, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def employees(self, request, pk=None):
        """
        GET /api/networks/{id}/employees/
        Сотрудники сети.
        """
        network = self.get_object()
        
        # Все сотрудники сети
        employees = network.employees.all().select_related('profile')
        
        # Фильтрация
        role_filter = request.query_params.get('role')
        
        if role_filter:
            employees = employees.filter(role=role_filter)
        
        # Пагинация
        page = self.paginate_queryset(employees)
        if page is not None:
            from apps.users.serializers import UserShortSerializer
            serializer = UserShortSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        from apps.users.serializers import UserShortSerializer
        serializer = UserShortSerializer(employees, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_administrator(self, request, pk=None):
        """
        POST /api/networks/{id}/add-administrator/
        Добавить администратора сети.
        """
        network = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            from apps.users.models import User
            user = User.objects.get(id=user_id)
            
            if user.role not in ['network_admin', 'admin']:
                return Response(
                    {'error': 'Пользователь должен иметь роль администратора сети'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            network.administrators.add(user)
            return Response({'status': 'Администратор добавлен'})
        
        except User.DoesNotExist:
            return Response(
                {'error': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_administrator(self, request, pk=None):
        """
        POST /api/networks/{id}/remove-administrator/
        Удалить администратора сети.
        """
        network = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            from apps.users.models import User
            user = User.objects.get(id=user_id)
            
            if network.administrators.count() <= 1:
                return Response(
                    {'error': 'Нельзя удалить последнего администратора'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            network.administrators.remove(user)
            return Response({'status': 'Администратор удален'})
        
        except User.DoesNotExist:
            return Response(
                {'error': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['patch'])
    def update_budget(self, request, pk=None):
        """
        PATCH /api/networks/{id}/update-budget/
        Обновить бюджет сети.
        """
        network = self.get_object()
        new_budget = request.data.get('monthly_budget')
        
        if new_budget is None:
            return Response(
                {'error': 'Не указана сумма бюджета'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_budget = float(new_budget)
            update_network_budget(network, new_budget)
            return Response({'status': 'Бюджет обновлен'})
        
        except ValueError:
            return Response(
                {'error': 'Некорректная сумма'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def settings(self, request, pk=None):
        """
        GET /api/networks/{id}/settings/
        Настройки сети.
        """
        network = self.get_object()
        settings, created = NetworkSettings.objects.get_or_create(network=network)
        serializer = NetworkSettingsSerializer(settings)
        return Response(serializer.data)
    
    @action(detail=True, methods=['put'])
    def update_settings(self, request, pk=None):
        """
        PUT /api/networks/{id}/update-settings/
        Обновить настройки сети.
        """
        network = self.get_object()
        settings = get_object_or_404(NetworkSettings, network=network)
        
        serializer = NetworkSettingsSerializer(
            settings, 
            data=request.data, 
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)


class StoreViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления магазинами.
    """
    queryset = Store.objects.all().select_related('network', 'manager')
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = StoreFilter
    search_fields = ['name', 'store_code', 'address', 'city']
    ordering_fields = ['name', 'city', 'opened_at']
    
    def get_permissions(self):
        """
        Динамические разрешения в зависимости от действия.
        """
        if self.action in ['create']:
            self.permission_classes = [IsAuthenticated, IsNetworkAdmin | IsAdminUser]
        elif self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, CanManageStore]
        return super().get_permissions()
    
    def get_queryset(self):
        """
        Фильтрация магазинов в зависимости от роли пользователя.
        """
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            return self.queryset.all()
        
        # Магазины сети, где пользователь администратор
        if user.role == 'network_admin':
            return self.queryset.filter(
                network__administrators=user
            )
        
        # Магазины, где пользователь менеджер
        if user.role == 'store_manager':
            return self.queryset.filter(
                Q(manager=user) | Q(assignments__user=user)
            ).distinct()
        
        # Магазины, где пользователь сотрудник
        if user.role == 'buyer':
            return self.queryset.filter(
                network__employees=user
            )
        
        return Store.objects.none()
    
    def get_serializer_class(self):
        """
        Выбор сериализатора в зависимости от действия.
        """
        if self.action == 'create':
            return CreateStoreSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateStoreSerializer
        elif self.action == 'retrieve':
            return StoreDetailSerializer
        return StoreSerializer
    
    def perform_create(self, serializer):
        """
        Создание магазина с проверкой прав.
        """
        network = serializer.validated_data['network']
        
        # Проверяем, что пользователь может создавать магазины в этой сети
        if not (self.request.user.is_superuser or 
                self.request.user.role == 'admin' or
                network.administrators.filter(id=self.request.user.id).exists()):
            raise PermissionError('У вас нет прав для создания магазина в этой сети')
        
        serializer.save()
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        GET /api/stores/{id}/stats/
        Статистика магазина.
        """
        store = self.get_object()
        stats = calculate_store_stats(store)
        serializer = StoreStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        """
        GET /api/stores/{id}/dashboard/
        Дашборд магазина.
        """
        store = self.get_object()
        dashboard_data = get_store_dashboard(store)
        return Response(dashboard_data)
    
    @action(detail=True, methods=['get'])
    def orders(self, request, pk=None):
        """
        GET /api/stores/{id}/orders/
        Заказы магазина.
        """
        store = self.get_object()
        
        from apps.orders.models import Order
        orders = Order.objects.filter(store=store).order_by('-created_at')
        
        # Фильтрация
        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if status_filter:
            orders = orders.filter(status=status_filter)
        if date_from:
            orders = orders.filter(created_at__date__gte=date_from)
        if date_to:
            orders = orders.filter(created_at__date__lte=date_to)
        
        # Пагинация
        page = self.paginate_queryset(orders)
        if page is not None:
            from apps.orders.serializers import OrderShortSerializer
            serializer = OrderShortSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        from apps.orders.serializers import OrderShortSerializer
        serializer = OrderShortSerializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def employees(self, request, pk=None):
        """
        GET /api/stores/{id}/employees/
        Сотрудники магазина.
        """
        store = self.get_object()
        
        # Менеджер и назначенные сотрудники
        employees = store.get_employees()
        
        page = self.paginate_queryset(employees)
        if page is not None:
            from apps.users.serializers import UserShortSerializer
            serializer = UserShortSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        from apps.users.serializers import UserShortSerializer
        serializer = UserShortSerializer(employees, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign_employee(self, request, pk=None):
        """
        POST /api/stores/{id}/assign-employee/
        Назначить сотрудника на магазин.
        """
        store = self.get_object()
        user_id = request.data.get('user_id')
        role = request.data.get('role', 'Сотрудник')
        is_primary = request.data.get('is_primary', False)
        
        try:
            from apps.users.models import User
            user = User.objects.get(id=user_id)
            
            # Проверяем, что пользователь является сотрудником сети
            if user not in store.network.employees.all():
                return Response(
                    {'error': 'Пользователь не является сотрудником этой сети'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            assignment = assign_user_to_store(
                user=user,
                store=store,
                role=role,
                is_primary=is_primary,
                assigned_by=request.user
            )
            
            serializer = StoreAssignmentSerializer(assignment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except User.DoesNotExist:
            return Response(
                {'error': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_employee(self, request, pk=None):
        """
        POST /api/stores/{id}/remove-employee/
        Удалить сотрудника из магазина.
        """
        store = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            from apps.users.models import User
            user = User.objects.get(id=user_id)
            
            remove_user_from_store(user, store)
            return Response({'status': 'Сотрудник удален из магазина'})
        
        except User.DoesNotExist:
            return Response(
                {'error': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['patch'])
    def update_budget(self, request, pk=None):
        """
        PATCH /api/stores/{id}/update-budget/
        Обновить бюджет магазина.
        """
        store = self.get_object()
        new_budget = request.data.get('monthly_budget')
        
        if new_budget is None:
            return Response(
                {'error': 'Не указана сумма бюджета'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_budget = float(new_budget)
            update_store_budget(store, new_budget)
            return Response({'status': 'Бюджет обновлен'})
        
        except ValueError:
            return Response(
                {'error': 'Некорректная сумма'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """
        POST /api/stores/{id}/change-status/
        Изменить статус магазина.
        """
        store = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Store.StoreStatus.choices):
            return Response(
                {'error': 'Некорректный статус'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        store.status = new_status
        store.save()
        
        return Response({
            'status': 'Статус обновлен',
            'new_status': new_status
        })


class MyNetworksView(APIView):
    """
    Сети текущего пользователя.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/networks/my-networks/
        Получить сети текущего пользователя.
        """
        user = request.user
        
        if user.is_superuser or user.role == 'admin':
            networks = RetailNetwork.objects.all()
        elif user.role == 'network_admin':
            networks = RetailNetwork.objects.filter(
                Q(administrators=user) | Q(created_by=user)
            ).distinct()
        elif user.role == 'store_manager':
            networks = RetailNetwork.objects.filter(
                stores__manager=user
            ).distinct()
        elif user.role == 'buyer':
            networks = RetailNetwork.objects.filter(
                Q(employees=user) |
                Q(stores__assignments__user=user)
            ).distinct()
        else:
            networks = RetailNetwork.objects.none()
        
        serializer = RetailNetworkSerializer(networks, many=True)
        return Response(serializer.data)


class MyStoresView(APIView):
    """
    Магазины текущего пользователя.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/networks/my-stores/
        Получить магазины текущего пользователя.
        """
        user = request.user
        
        if user.is_superuser or user.role == 'admin':
            stores = Store.objects.all()
        elif user.role == 'network_admin':
            stores = Store.objects.filter(
                network__administrators=user
            )
        elif user.role == 'store_manager':
            stores = Store.objects.filter(
                Q(manager=user) | Q(assignments__user=user)
            ).distinct()
        elif user.role == 'buyer':
            stores = Store.objects.filter(
                network__employees=user
            )
        else:
            stores = Store.objects.none()
        
        serializer = StoreSerializer(stores, many=True)
        return Response(serializer.data)
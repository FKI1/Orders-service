from rest_framework import viewsets, status, filters, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse
from datetime import timedelta

from .models import User, UserProfile, UserActivity, PasswordResetToken, Address
from .serializers import (
    UserSerializer,
    UserDetailSerializer,
    UserProfileSerializer,
    UserActivitySerializer,
    RegisterSerializer,
    UpdateUserSerializer,
    ChangePasswordSerializer,
    ResetPasswordSerializer,
    UserStatsSerializer,
    AddressSerializer,
    EmailVerificationSerializer,
    EmailVerificationResponseSerializer
)
from .permissions import (
    CanViewUser,
    CanUpdateUser,
    CanDeleteUser,
    IsOwnerOrAdmin
)
from .filters import UserFilter
from .services import (
    register_user,
    update_user_profile,
    change_user_password,
    reset_user_password,
    log_user_activity,
    create_password_reset_token,
    get_user_statistics,
    EmailVerificationService,
    AddressService
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Кастомный view для получения JWT токена.
    """
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Логируем вход в систему
            user = User.objects.get(email=request.data['email'])
            log_user_activity(
                user=user,
                activity_type='login',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Добавляем информацию о подтверждении email в ответ
            response.data['email_verified'] = user.email_verified
        
        return response


class SendVerificationEmailView(APIView):
    """
    Отправка письма с подтверждением email.
    POST /api/users/send-verification-email/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # Проверяем, не подтвержден ли уже email
        if user.email_verified:
            return Response(
                {'error': 'Email уже подтвержден'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Отправляем письмо
        success, message = EmailVerificationService.send_verification_email(user, request)
        
        if success:
            return Response({
                'success': True,
                'message': message,
                'email': user.email
            })
        else:
            return Response({
                'error': message
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResendVerificationEmailView(APIView):
    """
    Повторная отправка письма подтверждения.
    POST /api/users/resend-verification-email/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        success, message = EmailVerificationService.resend_verification_email(user, request)
        
        if success:
            return Response({
                'success': True,
                'message': message
            })
        else:
            return Response({
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    """
    Подтверждение email по токену.
    GET /api/users/verify-email/?token=...
    POST /api/users/verify-email/ (с токеном в теле)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token')
        
        if not token:
            return Response({
                'error': 'Токен не предоставлен'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return self._verify_email(token, request)

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        return self._verify_email(token, request)

    def _verify_email(self, token, request):
        user, message = EmailVerificationService.verify_email(token)
        
        if user:
            # Генерируем новые токены для автоматического входа
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'success': True,
                'message': message,
                'email_verified': True,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            })
        else:
            return Response({
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailRedirectView(APIView):
    """
    Перенаправление с токеном для веб-интерфейса.
    GET /api/users/verify-email/<str:token>/
    """
    permission_classes = [AllowAny]

    def get(self, request, token):
        user, message = EmailVerificationService.verify_email(token)
        
        # Перенаправляем на фронтенд с результатом
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        
        if user:
            redirect_url = f"{frontend_url}/email-verified?success=true&message={message}"
        else:
            redirect_url = f"{frontend_url}/email-verified?success=false&error={message}"
        
        return HttpResponseRedirect(redirect_url)


class VerificationStatusView(APIView):
    """
    Проверка статуса подтверждения email.
    GET /api/users/verification-status/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        status = EmailVerificationService.check_verification_status(request.user)
        return Response(status)


class AddressViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления адресами доставки пользователя.
    
    list: GET /api/users/addresses/
    create: POST /api/users/addresses/
    retrieve: GET /api/users/addresses/{id}/
    update: PUT /api/users/addresses/{id}/
    partial_update: PATCH /api/users/addresses/{id}/
    destroy: DELETE /api/users/addresses/{id}/
    """
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Только адреса текущего пользователя"""
        return Address.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')
    
    def perform_create(self, serializer):
        """Создание нового адреса"""
        address = serializer.save(user=self.request.user)
        
        # Логируем создание адреса
        log_user_activity(
            user=self.request.user,
            activity_type='address_create',
            description=f'Добавлен адрес: {address.short_address}',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata={'address_id': address.id, 'address_type': address.address_type}
        )
    
    def perform_update(self, serializer):
        """Обновление адреса"""
        address = serializer.save()
        
        # Логируем обновление адреса
        log_user_activity(
            user=self.request.user,
            activity_type='address_update',
            description=f'Обновлен адрес: {address.short_address}',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata={'address_id': address.id}
        )
    
    def perform_destroy(self, instance):
        """Удаление адреса"""
        address_info = instance.short_address
        
        # Логируем удаление адреса
        log_user_activity(
            user=self.request.user,
            activity_type='address_delete',
            description=f'Удален адрес: {address_info}',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata={'address_id': instance.id}
        )
        
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """
        POST /api/users/addresses/{id}/set_default/
        Установить адрес как основной.
        """
        address = self.get_object()
        
        try:
            address = AddressService.set_default_address(request.user, address.id)
            serializer = self.get_serializer(address)
            
            # Логируем установку основного адреса
            log_user_activity(
                user=request.user,
                activity_type='address_set_default',
                description=f'Установлен основной адрес: {address.short_address}',
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'address_id': address.id}
            )
            
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def default(self, request):
        """
        GET /api/users/addresses/default/
        Получить основной адрес пользователя.
        """
        address = AddressService.get_default_address(request.user)
        
        if address:
            serializer = self.get_serializer(address)
            return Response(serializer.data)
        else:
            return Response(
                {'detail': 'Основной адрес не установлен'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """
        POST /api/users/addresses/bulk_delete/
        Удаление нескольких адресов.
        """
        address_ids = request.data.get('address_ids', [])
        
        if not address_ids:
            return Response(
                {'error': 'Не указаны адреса для удаления'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем адреса пользователя
        addresses = Address.objects.filter(
            user=request.user,
            id__in=address_ids
        )
        
        deleted_count = addresses.count()
        addresses_info = [addr.short_address for addr in addresses]
        
        # Удаляем
        addresses.delete()
        
        # Логируем массовое удаление
        log_user_activity(
            user=request.user,
            activity_type='address_delete',
            description=f'Удалено адресов: {deleted_count}',
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'address_ids': address_ids, 'count': deleted_count}
        )
        
        return Response({
            'message': f'Удалено адресов: {deleted_count}',
            'deleted_count': deleted_count,
            'deleted_addresses': addresses_info
        })
    
    @action(detail=False, methods=['get'])
    def count(self, request):
        """
        GET /api/users/addresses/count/
        Получить количество адресов пользователя.
        """
        count = Address.objects.filter(user=request.user).count()
        return Response({'count': count})


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления пользователями.
    """
    queryset = User.objects.all().select_related('profile', 'company')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['email', 'first_name', 'last_name', 'phone', 'company_name']
    ordering_fields = ['email', 'first_name', 'last_name', 'date_joined', 'last_login']
    
    def get_permissions(self):
        """
        Динамические разрешения в зависимости от действия.
        """
        if self.action == 'list':
            self.permission_classes = [IsAuthenticated, CanViewUser]
        elif self.action == 'retrieve':
            self.permission_classes = [IsAuthenticated, CanViewUser]
        elif self.action == 'create':
            self.permission_classes = [IsAdminUser]
        elif self.action in ['update', 'partial_update']:
            self.permission_classes = [IsAuthenticated, CanUpdateUser]
        elif self.action == 'destroy':
            self.permission_classes = [IsAuthenticated, CanDeleteUser]
        else:
            self.permission_classes = [IsAuthenticated]
        
        return super().get_permissions()
    
    def get_queryset(self):
        """
        Фильтрация пользователей в зависимости от прав.
        """
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            return self.queryset.all()
        
        if user.role == 'network_admin' and user.company:
            return self.queryset.filter(
                Q(company=user.company) |
                Q(id=user.id)
            )
        
        if user.role == 'supplier' or user.role == 'buyer':
            return self.queryset.filter(id=user.id)
        
        return User.objects.none()
    
    def get_serializer_class(self):
        """
        Выбор сериализатора в зависимости от действия.
        """
        if self.action == 'create':
            return RegisterSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateUserSerializer
        elif self.action == 'retrieve':
            return UserDetailSerializer
        return UserSerializer
    
    def perform_create(self, serializer):
        """
        Создание пользователя.
        """
        user = serializer.save()
        UserProfile.objects.create(user=user)
        
        # Отправляем письмо с подтверждением email
        try:
            EmailVerificationService.send_verification_email(user, self.request)
        except Exception as e:
            # Логируем ошибку, но не прерываем создание
            print(f"Error sending verification email: {e}")
        
        log_user_activity(
            user=user,
            activity_type='profile_update',
            description='Пользователь создан',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
    
    def perform_update(self, serializer):
        """
        Обновление пользователя.
        """
        old_user = self.get_object()
        user = serializer.save()
        
        # Если email изменился, сбрасываем подтверждение
        if old_user.email != user.email:
            user.email_verified = False
            user.email_verification_token = None
            user.email_verification_sent_at = None
            user.save()
            
            # Отправляем новое письмо подтверждения
            try:
                EmailVerificationService.send_verification_email(user, self.request)
            except Exception as e:
                print(f"Error sending verification email: {e}")
        
        log_user_activity(
            user=user,
            activity_type='profile_update',
            description='Профиль обновлен',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
    
    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        """Получить профиль пользователя"""
        user = self.get_object()
        profile, created = UserProfile.objects.get_or_create(user=user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """Получить активность пользователя"""
        user = self.get_object()
        activities = user.activities.all().order_by('-created_at')
        
        page = self.paginate_queryset(activities)
        if page is not None:
            serializer = UserActivitySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = UserActivitySerializer(activities, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Получить статистику пользователя"""
        user = self.get_object()
        stats = get_user_statistics(user)
        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Активировать пользователя"""
        if not request.user.is_superuser and request.user.role != 'admin':
            return Response(
                {'error': 'Только администраторы могут активировать пользователей'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        user.is_active = True
        user.save()
        
        return Response({'success': 'Пользователь активирован'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Деактивировать пользователя"""
        if not request.user.is_superuser and request.user.role != 'admin':
            return Response(
                {'error': 'Только администраторы могут деактивировать пользователей'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        user.is_active = False
        user.save()
        
        return Response({'success': 'Пользователь деактивирован'})
    
    @action(detail=True, methods=['post'])
    def change_role(self, request, pk=None):
        """Изменить роль пользователя"""
        if not request.user.is_superuser and request.user.role != 'admin':
            return Response(
                {'error': 'Только администраторы могут изменять роли пользователей'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        new_role = request.data.get('role')
        
        if new_role not in dict(User.Role.choices):
            return Response(
                {'error': 'Некорректная роль'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.role = new_role
        user.save()
        
        return Response({'success': f'Роль изменена на {user.get_role_display()}'})
    
    @action(detail=True, methods=['post'])
    def send_verification(self, request, pk=None):
        """
        POST /api/users/{id}/send-verification/
        Отправить письмо подтверждения email пользователю.
        """
        if not request.user.is_superuser and request.user.role != 'admin':
            return Response(
                {'error': 'Только администраторы могут отправлять подтверждение'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        
        if user.email_verified:
            return Response(
                {'error': 'Email уже подтвержден'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = EmailVerificationService.send_verification_email(user, request)
        
        if success:
            return Response({'success': message})
        else:
            return Response(
                {'error': message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления профилями пользователей.
    """
    queryset = UserProfile.objects.all().select_related('user')
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        """
        Фильтрация профилей в зависимости от прав.
        """
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            return self.queryset.all()
        
        return self.queryset.filter(user=user)
    
    def perform_update(self, serializer):
        """
        Обновление профиля.
        """
        profile = serializer.save()
        
        log_user_activity(
            user=profile.user,
            activity_type='profile_update',
            description='Профиль пользователя обновлен',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )


class CurrentUserView(APIView):
    """
    Текущий пользователь.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/users/me/
        Получить информацию о текущем пользователе.
        """
        serializer = UserDetailSerializer(request.user)
        data = serializer.data
        # Добавляем информацию о подтверждении email
        data['email_verified'] = request.user.email_verified
        data['email_verification_required'] = not request.user.email_verified
        return Response(data)
    
    def put(self, request):
        """
        PUT /api/users/me/
        Обновить информацию о текущем пользователе.
        """
        serializer = UpdateUserSerializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        log_user_activity(
            user=request.user,
            activity_type='profile_update',
            description='Профиль обновлен',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response(serializer.data)


class CurrentUserProfileView(APIView):
    """
    Профиль текущего пользователя.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/users/me/profile/
        Получить профиль текущего пользователя.
        """
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    
    def put(self, request):
        """
        PUT /api/users/me/profile/
        Обновить профиль текущего пользователя.
        """
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(
            profile, 
            data=request.data, 
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        log_user_activity(
            user=request.user,
            activity_type='profile_update',
            description='Настройки профиля обновлены',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response(serializer.data)


class RegisterView(APIView):
    """
    Регистрация пользователя.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        POST /api/users/register/
        Зарегистрировать нового пользователя.
        """
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = register_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                first_name=serializer.validated_data.get('first_name', ''),
                last_name=serializer.validated_data.get('last_name', ''),
                role=serializer.validated_data.get('role', User.Role.BUYER),
                phone=serializer.validated_data.get('phone', ''),
                company_name=serializer.validated_data.get('company_name', '')
            )
            
            # Логируем регистрацию
            log_user_activity(
                user=user,
                activity_type='profile_update',
                description='Пользователь зарегистрирован',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Отправляем письмо с подтверждением email
            EmailVerificationService.send_verification_email(user, request)
            
            # Создаем JWT токены
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'email_verified': False,
                'message': 'Регистрация успешна. Проверьте email для подтверждения.'
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ChangePasswordView(APIView):
    """
    Смена пароля.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        POST /api/users/change-password/
        Сменить пароль текущего пользователя.
        """
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            change_user_password(
                user=request.user,
                old_password=serializer.validated_data['old_password'],
                new_password=serializer.validated_data['new_password']
            )
            
            log_user_activity(
                user=request.user,
                activity_type='password_change',
                description='Пароль изменен',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return Response({'success': 'Пароль успешно изменен'})
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ResetPasswordView(APIView):
    """
    Сброс пароля.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        POST /api/users/reset-password/
        Запросить сброс пароля.
        """
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            token = create_password_reset_token(user)
            
            # В реальном проекте здесь должна быть отправка email
            # send_password_reset_email(user, token.token, request)
            
            return Response({
                'success': 'Инструкции по сбросу пароля отправлены на email',
                'token': token.token  # Только для разработки!
            })
        
        except User.DoesNotExist:
            return Response({
                'success': 'Если пользователь с таким email существует, инструкции отправлены'
            })


class ConfirmResetPasswordView(APIView):
    """
    Подтверждение сброса пароля.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        POST /api/users/confirm-reset-password/
        Подтвердить сброс пароля.
        """
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token_str = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        try:
            token = PasswordResetToken.objects.get(
                token=token_str,
                is_used=False,
                expires_at__gt=timezone.now()
            )
            
            reset_user_password(token.user, new_password)
            token.is_used = True
            token.save()
            
            log_user_activity(
                user=token.user,
                activity_type='password_change',
                description='Пароль сброшен через восстановление',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return Response({'success': 'Пароль успешно изменен'})
        
        except PasswordResetToken.DoesNotExist:
            return Response(
                {'error': 'Неверный или просроченный токен'},
                status=status.HTTP_400_BAD_REQUEST
            )


class LogoutView(APIView):
    """
    Выход из системы.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        POST /api/users/logout/
        Выйти из системы.
        """
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            log_user_activity(
                user=request.user,
                activity_type='logout',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({'success': 'Успешный выход из системы'})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserStatsView(APIView):
    """
    Статистика пользователей.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        """
        GET /api/users/stats/
        Получить общую статистику пользователей.
        """
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        verified_users = User.objects.filter(is_verified=True).count()
        email_verified_users = User.objects.filter(email_verified=True).count()
        
        users_by_role = User.objects.values('role').annotate(
            count=Count('id')
        ).order_by('-count')
        
        role_stats = {
            item['role']: item['count']
            for item in users_by_role
        }
        
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        today_users = User.objects.filter(date_joined__date=today).count()
        week_users = User.objects.filter(date_joined__date__gte=week_ago).count()
        month_users = User.objects.filter(date_joined__date__gte=month_ago).count()
        
        active_today = User.objects.filter(
            last_login__date=today
        ).count()
        
        # Статистика по подтверждению email
        email_verification_stats = {
            'verified': email_verified_users,
            'unverified': total_users - email_verified_users,
            'verification_rate': round(email_verified_users / total_users * 100, 2) if total_users > 0 else 0
        }
        
        return Response({
            'total_users': total_users,
            'active_users': active_users,
            'verified_users': verified_users,
            'email_verified_users': email_verified_users,
            'email_verification_stats': email_verification_stats,
            'users_by_role': role_stats,
            'today_registrations': today_users,
            'week_registrations': week_users,
            'month_registrations': month_users,
            'active_today': active_today,
            'timestamp': timezone.now().isoformat()
        })


class MyActivitiesView(APIView):
    """
    Активность текущего пользователя.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/users/me/activities/
        Получить активность текущего пользователя.
        """
        activities = request.user.activities.all().order_by('-created_at')[:50]
        serializer = UserActivitySerializer(activities, many=True)
        return Response(serializer.data)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from .views import CustomTokenObtainPairView

# Основной роутер для ViewSet'ов
router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'profiles', views.UserProfileViewSet, basename='profile')


router.register(r'addresses', views.AddressViewSet, basename='address')

urlpatterns = [

    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    

    path('register/', views.RegisterView.as_view(), name='register'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),
    path('confirm-reset-password/', views.ConfirmResetPasswordView.as_view(), name='confirm-reset-password'),
    

    path('me/', views.CurrentUserView.as_view(), name='current-user'),
    path('me/profile/', views.CurrentUserProfileView.as_view(), name='current-user-profile'),
    path('me/activities/', views.MyActivitiesView.as_view(), name='my-activities'),
    
    # Отправка/повторная отправка подтверждения
    path('send-verification-email/', 
         views.SendVerificationEmailView.as_view(), 
         name='send-verification-email'),
    
    path('resend-verification-email/', 
         views.ResendVerificationEmailView.as_view(), 
         name='resend-verification-email'),
    
    # Подтверждение email (API)
    path('verify-email/', 
         views.VerifyEmailView.as_view(), 
         name='verify-email-api'),
    
    # Подтверждение email (веб-редирект с токеном в URL)
    path('verify-email/<str:token>/', 
         views.VerifyEmailRedirectView.as_view(), 
         name='verify-email'),
    
    # Статус подтверждения email
    path('verification-status/', 
         views.VerificationStatusView.as_view(), 
         name='verification-status'),
    
    
    # Альтернативные маршруты для адресов (если нужно без router)
    path('addresses-list/', 
         views.AddressViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='address-list-alt'),
    
    path('addresses-default/', 
         views.AddressViewSet.as_view({'get': 'default'}), 
         name='address-default'),
    
    path('addresses-count/', 
         views.AddressViewSet.as_view({'get': 'count'}), 
         name='address-count'),
    
    path('addresses-bulk-delete/', 
         views.AddressViewSet.as_view({'post': 'bulk_delete'}), 
         name='address-bulk-delete'),
    

    path('', include(router.urls)),
    
    path('stats/', views.UserStatsView.as_view(), name='user-stats'),
    
    # Профиль пользователя
    path('users/<int:pk>/profile/', 
         views.UserViewSet.as_view({'get': 'profile'}), 
         name='user-profile'),
    
    # Активность пользователя
    path('users/<int:pk>/activities/', 
         views.UserViewSet.as_view({'get': 'activities'}), 
         name='user-activities'),
    
    # Статистика пользователя
    path('users/<int:pk>/stats/', 
         views.UserViewSet.as_view({'get': 'stats'}), 
         name='user-stats-detail'),
    
    # Активация/деактивация пользователя
    path('users/<int:pk>/activate/', 
         views.UserViewSet.as_view({'post': 'activate'}), 
         name='user-activate'),
    
    path('users/<int:pk>/deactivate/', 
         views.UserViewSet.as_view({'post': 'deactivate'}), 
         name='user-deactivate'),
    
    # Смена роли пользователя
    path('users/<int:pk>/change-role/', 
         views.UserViewSet.as_view({'post': 'change_role'}), 
         name='user-change-role'),
    
    # === ДОБАВЛЕНО: Отправка подтверждения email для конкретного пользователя (админ) ===
    path('users/<int:pk>/send-verification/', 
         views.UserViewSet.as_view({'post': 'send_verification'}), 
         name='user-send-verification'),
]


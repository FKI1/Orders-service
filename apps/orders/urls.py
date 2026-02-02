from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'orders', views.OrderViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('orders/<int:pk>/status/', views.OrderViewSet.as_view({'patch': 'status'})),
    path('orders/<int:pk>/cancel/', views.OrderViewSet.as_view({'post': 'cancel'})),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'reports', views.ReportViewSet, basename='report')
router.register(r'schedules', views.ReportScheduleViewSet, basename='schedule')

urlpatterns = [
    path('', include(router.urls)),
    path('parameters/<str:report_type>/', 
         views.ReportParametersView.as_view(), 
         name='report-parameters'),
]

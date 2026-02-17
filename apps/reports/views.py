from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from .models import Report, ReportSchedule
from .serializers import (
    ReportSerializer,
    ReportDetailSerializer,
    ReportCreateSerializer,
    ReportScheduleSerializer,
    ReportScheduleCreateSerializer,
    ReportParameterSerializer
)
from .services import ReportGenerator, ReportScheduler
from apps.core.permissions import IsAdminOrReadOnly


class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления отчетами.
    """
    queryset = Report.objects.all().select_related('created_by')
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['report_type', 'status', 'format']
    search_fields = ['report_number', 'report_type']
    ordering_fields = ['created_at', 'completed_at', 'status']
    
    def get_queryset(self):
        """Фильтрация отчетов в зависимости от прав"""
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            return self.queryset.all()
        
        # Пользователи видят только свои отчеты
        return self.queryset.filter(created_by=user)
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return ReportCreateSerializer
        elif self.action == 'retrieve':
            return ReportDetailSerializer
        return ReportSerializer
    
    def perform_create(self, serializer):
        """Создание отчета"""
        report = serializer.save(created_by=self.request.user)
        
        # Запускаем генерацию отчета асинхронно
        from config.celery import current_app
        current_app.send_task('generate_report', args=[report.id])
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        GET /api/reports/{id}/download/
        Скачать файл отчета.
        """
        report = self.get_object()
        
        if not report.is_ready:
            return Response(
                {'error': 'Отчет еще не готов'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            response = FileResponse(
                report.file.open('rb'),
                content_type=f'application/{report.format}'
            )
            response['Content-Disposition'] = f'attachment; filename="{report.filename}"'
            return response
        except FileNotFoundError:
            raise Http404("Файл отчета не найден")
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """
        POST /api/reports/{id}/regenerate/
        Перегенерировать отчет.
        """
        report = self.get_object()
        
        # Создаем новый отчет на основе старого
        new_report = Report.objects.create(
            report_type=report.report_type,
            format=report.format,
            parameters=report.parameters,
            created_by=request.user
        )
        
        # Запускаем генерацию
        from config.celery import current_app
        current_app.send_task('generate_report', args=[new_report.id])
        
        serializer = self.get_serializer(new_report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        POST /api/reports/{id}/cancel/
        Отменить генерацию отчета.
        """
        report = self.get_object()
        
        if report.status not in [Report.ReportStatus.PENDING, Report.ReportStatus.PROCESSING]:
            return Response(
                {'error': 'Нельзя отменить отчет в текущем статусе'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report.status = Report.ReportStatus.CANCELLED
        report.completed_at = timezone.now()
        report.save()
        
        return Response({'success': 'Отчет отменен'})


class ReportScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления расписаниями отчетов.
    """
    queryset = ReportSchedule.objects.all().select_related('created_by')
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['report_type', 'frequency', 'is_active']
    search_fields = ['name']
    
    def get_queryset(self):
        """Фильтрация расписаний"""
        user = self.request.user
        
        if user.is_superuser or user.role == 'admin':
            return self.queryset.all()
        
        return self.queryset.filter(created_by=user)
    
    def get_serializer_class(self):
        """Выбор сериализатора"""
        if self.action == 'create':
            return ReportScheduleCreateSerializer
        return ReportScheduleSerializer
    
    def perform_create(self, serializer):
        """Создание расписания"""
        schedule = serializer.save(created_by=self.request.user)
        
        # Устанавливаем следующую дату запуска
        from .services import ReportScheduler
        schedule.next_run = ReportScheduler.calculate_next_run(schedule)
        schedule.save()
    
    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """
        POST /api/report-schedules/{id}/run-now/
        Запустить отчет по расписанию немедленно.
        """
        schedule = self.get_object()
        
        # Создаем отчет
        report = Report.objects.create(
            report_type=schedule.report_type,
            format=schedule.format,
            parameters=schedule.parameters,
            created_by=request.user
        )
        
        # Запускаем генерацию
        from config.celery import current_app
        current_app.send_task('generate_report', args=[report.id])
        
        serializer = ReportSerializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def available_reports(self, request):
        """
        GET /api/report-schedules/available-reports/
        Список доступных типов отчетов.
        """
        return Response([
            {'value': value, 'label': label}
            for value, label in Report.ReportType.choices
        ])


class ReportParametersView(APIView):
    """
    Получение параметров для отчета.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, report_type):
        """
        GET /api/reports/parameters/{report_type}/
        Получить параметры для конкретного типа отчета.
        """
        parameters = {
            'orders_daily': {
                'date_from': timezone.now().date(),
                'date_to': timezone.now().date(),
                'store_id': None,
                'status': None,
            },
            'orders_weekly': {
                'date_from': timezone.now().date() - timedelta(days=7),
                'date_to': timezone.now().date(),
                'store_id': None,
                'status': None,
            },
            'orders_monthly': {
                'date_from': timezone.now().date().replace(day=1),
                'date_to': timezone.now().date(),
                'store_id': None,
                'status': None,
            },
            'products_inventory': {
                'category_id': None,
                'supplier_id': None,
                'show_zero_stock': True,
            },
            'products_low_stock': {
                'threshold': 10,
                'category_id': None,
                'supplier_id': None,
            },
            'users_registration': {
                'date_from': timezone.now().date() - timedelta(days=30),
                'date_to': timezone.now().date(),
                'role': None,
            },
            'financial_revenue': {
                'date_from': timezone.now().date().replace(day=1),
                'date_to': timezone.now().date(),
                'group_by': 'day',
            },
        }
        
        return Response(parameters.get(report_type, {}))

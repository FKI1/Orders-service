from django.contrib import admin
from django.utils.html import format_html
from .models import Report, ReportSchedule


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """
    Админка для отчетов.
    """
    list_display = [
        'report_number',
        'report_type_display',
        'format',
        'status_display',
        'created_by',
        'created_at',
        'file_link'
    ]
    
    list_filter = ['report_type', 'format', 'status', 'created_at']
    search_fields = ['report_number', 'created_by__email']
    readonly_fields = [
        'report_number', 'file', 'file_size', 'error_message',
        'created_at', 'started_at', 'completed_at', 'created_by'
    ]
    
    def report_type_display(self, obj):
        return obj.get_report_type_display()
    report_type_display.short_description = 'Тип отчета'
    
    def status_display(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray',
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_display.short_description = 'Статус'
    
    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">Скачать</a>',
                obj.file.url
            )
        return '-'
    file_link.short_description = 'Файл'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    """
    Админка для расписаний отчетов.
    """
    list_display = [
        'name',
        'report_type_display',
        'frequency',
        'is_active',
        'last_run',
        'next_run',
        'created_by'
    ]
    
    list_filter = ['report_type', 'frequency', 'is_active']
    search_fields = ['name', 'created_by__email']
    
    def report_type_display(self, obj):
        return obj.get_report_type_display()
    report_type_display.short_description = 'Тип отчета'

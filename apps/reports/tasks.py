from config.celery import shared_app
from django.utils import timezone
from .models import Report
from .services import ReportGenerator, ReportScheduler


@shared_app.task
def generate_report(report_id):
    """
    Асинхронная генерация отчета.
    """
    return ReportGenerator.generate_report(report_id)


@shared_app.task
def run_scheduled_reports():
    """
    Запуск отчетов по расписанию.
    """
    return ReportScheduler.run_scheduled_reports()


@shared_app.task
def cleanup_old_reports(days=30):
    """
    Очистка старых отчетов.
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    old_reports = Report.objects.filter(
        created_at__lt=cutoff_date,
        status=Report.ReportStatus.COMPLETED
    )
    
    count = old_reports.count()
    old_reports.delete()
    
    return f"Удалено {count} старых отчетов"

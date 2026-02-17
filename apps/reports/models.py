from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid


class Report(models.Model):
    """
    Модель для хранения сгенерированных отчетов.
    """
    class ReportType(models.TextChoices):
        # Отчеты по заказам
        ORDERS_DAILY = 'orders_daily', _('Ежедневный отчет по заказам')
        ORDERS_WEEKLY = 'orders_weekly', _('Еженедельный отчет по заказам')
        ORDERS_MONTHLY = 'orders_monthly', _('Ежемесячный отчет по заказам')
        ORDERS_CUSTOM = 'orders_custom', _('Пользовательский отчет по заказам')
        
        # Отчеты по товарам
        PRODUCTS_INVENTORY = 'products_inventory', _('Отчет по остаткам')
        PRODUCTS_SALES = 'products_sales', _('Отчет по продажам')
        PRODUCTS_POPULAR = 'products_popular', _('Популярные товары')
        PRODUCTS_LOW_STOCK = 'products_low_stock', _('Товары с низким остатком')
        
        # Отчеты по пользователям
        USERS_REGISTRATION = 'users_registration', _('Регистрация пользователей')
        USERS_ACTIVITY = 'users_activity', _('Активность пользователей')
        USERS_ROLES = 'users_roles', _('Распределение по ролям')
        
        # Отчеты по поставщикам
        SUPPLIERS_PERFORMANCE = 'suppliers_performance', _('Эффективность поставщиков')
        SUPPLIERS_PRODUCTS = 'suppliers_products', _('Товары поставщиков')
        
        # Финансовые отчеты
        FINANCIAL_REVENUE = 'financial_revenue', _('Выручка')
        FINANCIAL_PAYMENTS = 'financial_payments', _('Платежи')
        FINANCIAL_TAX = 'financial_tax', _('Налоговый отчет')
    
    class ReportFormat(models.TextChoices):
        PDF = 'pdf', _('PDF')
        EXCEL = 'excel', _('Excel')
        CSV = 'csv', _('CSV')
        JSON = 'json', _('JSON')
    
    class ReportStatus(models.TextChoices):
        PENDING = 'pending', _('В очереди')
        PROCESSING = 'processing', _('Генерация')
        COMPLETED = 'completed', _('Готов')
        FAILED = 'failed', _('Ошибка')
        CANCELLED = 'cancelled', _('Отменен')
    
    # Основная информация
    report_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        verbose_name=_('Номер отчета')
    )
    
    report_type = models.CharField(
        max_length=50,
        choices=ReportType.choices,
        verbose_name=_('Тип отчета')
    )
    
    format = models.CharField(
        max_length=20,
        choices=ReportFormat.choices,
        default=ReportFormat.EXCEL,
        verbose_name=_('Формат')
    )
    
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
        verbose_name=_('Статус')
    )
    
    # Параметры отчета
    parameters = models.JSONField(
        default=dict,
        verbose_name=_('Параметры'),
        help_text=_('Параметры генерации отчета (даты, фильтры и т.д.)')
    )
    
    # Результат
    file = models.FileField(
        upload_to='reports/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Файл отчета')
    )
    
    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Размер файла (байт)')
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Сообщение об ошибке')
    )
    
    # Временные метки
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Дата начала генерации')
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Дата завершения')
    )
    
    # Владелец отчета
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reports',
        verbose_name=_('Создатель')
    )
    
    class Meta:
        verbose_name = _('Отчет')
        verbose_name_plural = _('Отчеты')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_number']),
            models.Index(fields=['report_type']),
            models.Index(fields=['status']),
            models.Index(fields=['created_by']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.report_number}"
    
    def save(self, *args, **kwargs):
        if not self.report_number:
            self.report_number = self.generate_report_number()
        super().save(*args, **kwargs)
    
    def generate_report_number(self):
        """Генерация номера отчета"""
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4().hex[:6]).upper()
        return f"RPT-{date_str}-{random_str}"
    
    @property
    def processing_time(self):
        """Время генерации отчета"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        return None
    
    @property
    def filename(self):
        """Имя файла для скачивания"""
        if self.file:
            return self.file.name.split('/')[-1]
        return f"report_{self.report_number}.{self.format}"
    
    @property
    def is_ready(self):
        """Отчет готов к скачиванию"""
        return self.status == self.ReportStatus.COMPLETED and self.file


class ReportSchedule(models.Model):
    """
    Расписание автоматической генерации отчетов.
    """
    class Frequency(models.TextChoices):
        DAILY = 'daily', _('Ежедневно')
        WEEKLY = 'weekly', _('Еженедельно')
        MONTHLY = 'monthly', _('Ежемесячно')
        QUARTERLY = 'quarterly', _('Ежеквартально')
        YEARLY = 'yearly', _('Ежегодно')
    
    name = models.CharField(
        max_length=255,
        verbose_name=_('Название расписания')
    )
    
    report_type = models.CharField(
        max_length=50,
        choices=Report.ReportType.choices,
        verbose_name=_('Тип отчета')
    )
    
    format = models.CharField(
        max_length=20,
        choices=Report.ReportFormat.choices,
        default=Report.ReportFormat.EXCEL,
        verbose_name=_('Формат')
    )
    
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        verbose_name=_('Частота')
    )
    
    parameters = models.JSONField(
        default=dict,
        verbose_name=_('Параметры')
    )
    
    recipients = models.JSONField(
        default=list,
        verbose_name=_('Получатели'),
        help_text=_('Список email для отправки')
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Активно')
    )
    
    last_run = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Последний запуск')
    )
    
    next_run = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Следующий запуск')
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='report_schedules',
        verbose_name=_('Создатель')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления')
    )
    
    class Meta:
        verbose_name = _('Расписание отчетов')
        verbose_name_plural = _('Расписания отчетов')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"

import os
from celery import Celery
from celery.schedules import crontad
from django.conf import settings

# Устанавливаем переменную окружения для Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Создаем экземпляр Celery
app = Celery('order_service')

# Загружаем конфигурацию из Django settings с префиксом 'CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически обнаруживаем и регистрируем задачи из всех приложений
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    Отладочная задача для проверки работы Celery.
    """
    print(f'Request: {self.request!r}')


app.conf.beat_schedule = {
    'run-scheduled-reports': {
        'task': 'apps.reports.tasks.run_scheduled_reports',
        'schedule': crontab(minute=0, hour=1),  # Каждый день в 01:00
        'options': {'queue': 'reports'},
    },
    'cleanup-old-reports': {
        'task': 'apps.reports.tasks.cleanup_old_reports',
        'schedule': crontab(minute=0, hour=2, day_of_week=1),  # Каждый понедельник в 02:00
        'options': {'queue': 'maintenance'},
        'kwargs': {'days': 30},
    },
    
    'send-pending-emails': {
        'task': 'apps.users.tasks.send_pending_emails',
        'schedule': crontab(minute='*/15'),  # Каждые 15 минут
        'options': {'queue': 'emails'},
    },
    'cleanup-expired-tokens': {
        'task': 'apps.users.tasks.cleanup_expired_tokens',
        'schedule': crontab(minute=0, hour=3),  # Каждый день в 03:00
        'options': {'queue': 'maintenance'},
    },
    
    'check-pending-orders': {
        'task': 'apps.orders.tasks.check_pending_orders',
        'schedule': crontab(minute='*/30'),  # Каждые 30 минут
        'options': {'queue': 'orders'},
    },
    'update-order-statuses': {
        'task': 'apps.orders.tasks.update_order_statuses',
        'schedule': crontab(minute=0, hour='*/2'),  # Каждые 2 часа
        'options': {'queue': 'orders'},
    },
    
    'check-low-stock': {
        'task': 'apps.products.tasks.check_low_stock',
        'schedule': crontab(minute=0, hour=9),  # Каждый день в 09:00
        'options': {'queue': 'products'},
    },
    'update-product-ratings': {
        'task': 'apps.products.tasks.update_product_ratings',
        'schedule': crontab(minute=0, hour=4),  # Каждый день в 04:00
        'options': {'queue': 'products'},
    },
    
    'database-backup': {
        'task': 'apps.core.tasks.database_backup',
        'schedule': crontab(minute=0, hour=23),  # Каждый день в 23:00
        'options': {'queue': 'backup'},
    },
}

# Очереди задач
app.conf.task_queues = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'reports': {
        'exchange': 'reports',
        'routing_key': 'reports',
    },
    'emails': {
        'exchange': 'emails',
        'routing_key': 'emails',
    },
    'orders': {
        'exchange': 'orders',
        'routing_key': 'orders',
    },
    'products': {
        'exchange': 'products',
        'routing_key': 'products',
    },
    'maintenance': {
        'exchange': 'maintenance',
        'routing_key': 'maintenance',
    },
    'backup': {
        'exchange': 'backup',
        'routing_key': 'backup',
    },
}

# Маршрутизация задач по очередям
app.conf.task_routes = {
    'apps.reports.tasks.*': {'queue': 'reports'},
    'apps.users.tasks.send_*': {'queue': 'emails'},
    'apps.orders.tasks.*': {'queue': 'orders'},
    'apps.products.tasks.*': {'queue': 'products'},
    'apps.core.tasks.*': {'queue': 'maintenance'},
    '*.cleanup_*': {'queue': 'maintenance'},
    '*.backup': {'queue': 'backup'},
}

# Настройки выполнения задач
app.conf.task_soft_time_limit = 300  # 5 минут
app.conf.task_time_limit = 600       # 10 минут
app.conf.task_max_retries = 3
app.conf.task_retry_delay = 60       # 1 минута

# Настройки результата
app.conf.result_expires = 3600 * 24 * 7  # 7 дней
app.conf.task_ignore_result = False

# Настройки worker
app.conf.worker_max_tasks_per_child = 100
app.conf.worker_prefetch_multiplier = 4

# Сериализация
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']

# Timezone
app.conf.enable_utc = True
app.conf.timezone = 'Europe/Moscow'

# Отладка
app.conf.task_always_eager = settings.DEBUG
app.conf.task_eager_propagates = True

if __name__ == '__main__':
    app.start()
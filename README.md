  <h3>🚀 Полнофункциональная система управления заказами для розничной торговли</h3>
  
  [📖 Документация](#-документация) • 
  [🚀 Быстрый старт](#-быстрый-старт) • 
  [📦 API](#-api-endpoints) • 
  [🐳 Docker](#-docker) • 
  [📊 Отчеты](#-генерация-отчетов)
  
</div>

---

## 📋 Содержание

- [О проекте](#о-проекте)
- [Технологический стек](#технологический-стек)
- [Функциональные возможности](#функциональные-возможности)
- [Быстрый старт](#быстрый-старт)
- [Структура проекта](#структура-проекта)
- [API Endpoints](#api-endpoints)
- [Модели данных](#модели-данных)
- [Аутентификация](#аутентификация)
- [Генерация отчетов](#генерация-отчетов)
- [Docker](#docker)
- [Участие в разработке](#участие-в-разработке)


---

## 🎯 О проекте

**Order Service** - это современная, масштабируемая система управления заказами, разработанная для автоматизации процессов розничной торговли и B2B взаимодействий. Проект предоставляет мощное REST API с полной документацией, готовое для интеграции с любыми клиентскими приложениями.

### ✨ Ключевые возможности

| | | |
|:---:|:---:|:---:|
| 👥 **Пользователи**<br>Система ролей, профили | 📦 **Товары**<br>Категории, спецификации | 🛒 **Заказы**<br>Статусы, история |
| 📍 **Адреса**<br>Множественные, выбор основного | 📧 **Email**<br>Подтверждение, уведомления | 📊 **Отчеты**<br>Excel, PDF, CSV, JSON |
| ⚡ **Фоновые задачи**<br>Celery, Redis, периодические | 🔐 **Безопасность**<br>JWT токены, права доступа | 🐳 **Docker**<br>Контейнеризация, оркестрация |

---

## 🛠 Технологический стек

### 🏗️ Backend
* 🐍 **Python 3.11** - основной язык разработки
* 🎯 **Django 4.2** - веб-фреймворк
* 🔧 **Django REST Framework 3.14** - создание REST API
* ⚡ **Celery 5.3** - фоновые задачи и очередь
* 🔐 **JWT (Simple JWT)** - аутентификация
* 📝 **DRF-YASG** - документация API (Swagger/ReDoc)

### 🗄️ База данных и кэширование
* 🐘 **PostgreSQL 15** - основная база данных
* 📀 **Redis 7** - кэширование и брокер задач
* 🔍 **django-filter** - фильтрация данных

### ⚙️ Инфраструктура
* 🐳 **Docker** - контейнеризация приложения
* 🐙 **Docker Compose** - оркестрация контейнеров
* 🌐 **Nginx** - веб-сервер и обратный прокси
* 🚀 **Gunicorn** - WSGI сервер для production
* 📊 **Flower** - мониторинг Celery задач
* 📈 **Prometheus + Grafana** - мониторинг метрик

---

## 📦 Функциональные возможности

### 👥 **Пользователи и роли**

| Роль | Описание | Права |
|:-----|:---------|:------|
| **Admin** | Администратор системы | Полный доступ ко всем ресурсам |
| **Supplier** | Поставщик товаров | Управление своими товарами, просмотр заказов |
| **Buyer** | Закупщик | Создание заказов, управление адресами |
| **Network Admin** | Администратор сети | Управление магазинами своей сети |
| **Store Manager** | Менеджер магазина | Управление заказами магазина |

### 📦 **Товары**
- ✅ Категории товаров (неограниченная вложенность)
- ✅ Детальные спецификации с характеристиками
- ✅ Изображения товаров (основное/дополнительные)
- ✅ Отзывы и рейтинги
- ✅ Управление остатками и резервирование
- ✅ Поиск и фильтрация по параметрам

### 🛒 **Заказы**
- ✅ Создание и редактирование заказов
- ✅ Отслеживание статусов (черновик → доставлен)
- ✅ Управление оплатами
- ✅ История изменений
- ✅ Интеграция с адресами доставки
- ✅ Email уведомления о смене статуса

### 📍 **Адреса доставки**
- ✅ Множественные адреса для пользователя
- ✅ Типы адресов (домашний, рабочий, другой)
- ✅ Выбор основного адреса
- ✅ Детальная информация (подъезд, этаж, домофон)
- ✅ Снимок адреса в заказе (для истории)

### 📧 **Email подтверждение**
- ✅ Подтверждение email при регистрации
- ✅ Повторная отправка (с защитой от спама)
- ✅ Проверка срока действия токена (24 часа)
- ✅ HTML шаблоны писем

---

## 🚀 Быстрый старт

### Предварительные требования
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker 24+ (опционально)
- Git

### 📥 Установка

<details>
<summary><b>🔧 Вариант 1: Локальная установка</b></summary>
  
```bash
# 1. Клонировать репозиторий
git clone https://github.com/yourusername/order_service.git
cd order_service

# 2. Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Создать файл окружения
cp .env.example .env
# Отредактируйте .env под свои параметры

# 5. Применить миграции
python manage.py migrate

# 6. Создать суперпользователя
python manage.py createsuperuser

# 7. Запустить сервер
python manage.py runserver
```
</details> 

Сервер будет доступен по адресу: http://localhost:8000

<details> 
<summary><b>🐳 Вариант 2: Установка через Docker</b></summary>

  ```bash
# 1. Клонировать репозиторий
git clone https://github.com/yourusername/order_service.git
cd order_service

# 2. Создать файл окружения
cp .env.example .env

# 3. Запустить Docker Compose
docker-compose up -d --build

# 4. Применить миграции
docker-compose exec django python manage.py migrate

# 5. Создать суперпользователя
docker-compose exec django python manage.py createsuperuser

# 6. Проверить логи
docker-compose logs -f django
```
</details> 

### ✅ Проверка установки
```bash
# Проверить, что сервер работает
curl http://localhost:8000/health/

# Открыть в браузере
# Админка: http://localhost:8000/admin/
# Swagger: http://localhost:8000/api/docs/
# ReDoc: http://localhost:8000/api/redoc/
```
## 📁 Структура проекта
```bash
order_service/
├── 📦 .env.example
├── 🐳 docker-compose.yml
├── 🐳 .dockerignore
├── 🐳 Dockerfile
├── 📄 manage.py
├── 📄 requirements.txt
├── 📄 README.md
│
├── ⚙️ config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py
│
├── 📱 apps/
│   ├── 👥 users/
│   │   ├── admin.py
│   │   ├── models.py
│   │   ├── filters.py
│   │   ├── permissions.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── services.py
│   │
│   ├── 📦 products/
│   │   ├── models.py
│   │   ├── filters.py
│   │   ├── views.py
│   │   ├── permissions.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── services.py
│   │
│   ├── 🛒 orders/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── filters.py
│   │   ├── enums.py
│   │   ├── serializers.py
│   │   ├── permissions.py
│   │   ├── urls.py
│   │   ├── services.py
│   │
│   ├── 📊 reports/
│   │   ├── admin.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   └── tasks.py
│   │
│   ├── 🛍️ cart/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │
│   ├── 📊 analytics/
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── reports.py
│   │   ├── queries.py
│   │
│   ├── 🌐 networks/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── filters.py
│   │   ├── validators.py
│   │   ├── serializers.py
│   │   ├── permissions.py
│   │   ├── urls.py
│   │   ├── services.py
│   │
│   ├── 🤝 suppliers/
│   │   ├── views.py
│   │   ├── filters.py
│   │   ├── validators.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── services.py
│
├── 📧 templates/
│   └── emails/
│       ├── email_verification.html
│       ├── email_verification.txt
│       └── report_ready.html
│       └── report_ready.txt
```
## 🌐 API Endpoints

### 🔐 Аутентификация (/api/users/)
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | /auth/token/ | Получить JWT токен |
| POST | /auth/token/refresh/ | Обновить JWT токен |
| POST | /auth/logout/ | Выйти из системы |
| POST | /register/ | Регистрация пользователя |
| POST | /change-password/ | Смена пароля |
| POST | /reset-password/ | Запрос сброса пароля |
| POST | /confirm-reset-password/ | Подтверждение сброса |

### 📧 Email подтверждение
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | /send-verification-email/ | Отправить подтверждение |
| POST | /resend-verification-email/ | Повторная отправка |
| GET | /verify-email/?token=... | Подтвердить email |
| GET | /verify-email/<str:token>/ | Веб-редирект |
| GET | /verification-status/ | Статус подтверждения |

### 👤 Текущий пользователь
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | /me/ | Информация о пользователе |
| PUT | /me/ | Обновить профиль |
| GET | /me/profile/ | Получить профиль |
| PUT | /me/profile/ | Обновить настройки профиля |
| GET | /me/activities/ | Активность пользователя |

### 📍 Адреса доставки
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | /addresses/ | Список адресов |
| POST | /addresses/ | Создать адрес |
| GET | /addresses/{id}/ | Детали адреса |
| PUT | /addresses/{id}/ | Обновить адрес |
| PATCH | /addresses/{id}/ | Частичное обновление |
| DELETE | /addresses/{id}/ | Удалить адрес |
| POST | /addresses/{id}/set_default/ | Установить основным |
| GET | /addresses/default/ | Получить основной адрес |
| GET | /addresses/count/ | Количество адресов |
| POST | /addresses/bulk_delete/ | Массовое удаление |

### 📦 Товары (/api/products/)
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | / | Список товаров |
| POST | / | Создать товар |
| GET | /{id}/ | Детали товара |
| PUT | /{id}/ | Обновить товар |
| PATCH | /{id}/ | Частичное обновление |
| DELETE | /{id}/ | Удалить товар |
| GET | /search/ | Поиск товаров |
| GET | /popular/ | Популярные товары |
| GET | /recommended/ | Рекомендованные |
| GET | /new-arrivals/ | Новинки |
| GET | /bestsellers/ | Бестселлеры |
| GET | /my-products/ | Мои товары (для поставщиков) |

### 📊 Отчеты (/api/reports/)
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | / | Список отчетов |
| POST | / | Создать отчет |
| GET | /{id}/ | Детали отчета |
| DELETE | /{id}/ | Удалить отчет |
| GET | /{id}/download/ | Скачать файл |
| POST | /{id}/regenerate/ | Перегенерировать |
| POST | /{id}/cancel/ | Отменить генерацию |
| GET | /schedules/ | Список расписаний |
| POST | /schedules/ | Создать расписание |
| POST | /schedules/{id}/run-now/ | Запустить сейчас |

## 📊 Модели данных

### 👥 User
```python
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Администратор'
        SUPPLIER = 'supplier', 'Поставщик'
        BUYER = 'buyer', 'Закупщик'
    
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    phone = models.CharField(max_length=17, blank=True)
    email_verified = models.BooleanField(default=False)
    company = models.ForeignKey('networks.RetailNetwork', null=True)
```
### 📍 Address
```python
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=200)
    house = models.CharField(max_length=20)
    apartment = models.CharField(max_length=20, blank=True)
    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
```
### 📦 Product
```python
class Product(models.Model):
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
```
### 📦 ProductSpecification
```python
class ProductSpecification(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    brand = models.CharField(max_length=255, blank=True)
    manufacturer = models.CharField(max_length=255, blank=True)
    country_of_origin = models.CharField(max_length=100, blank=True)
    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    attributes = models.JSONField(default=dict)
```
### 🛒 Order
```python
class Order(models.Model):
    order_number = models.CharField(max_length=50, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    delivery_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
```
## 🔐 Аутентификация

### Получение токена
```bash
POST /api/users/auth/token/
{
    "email": "user@example.com",
    "password": "password123"
}
```
#### Ответ:
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "email_verified": true
}
```
### Использование токена
```bash
{
  Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
}
```
### Обновление токена
```bash
 POST /api/users/auth/token/refresh/
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

```
## 📊 Генерация отчетов

Система поддерживает создание различных типов отчетов в нескольких форматах.

### Типы отчетов

| Категория | Типы отчетов | Форматы |
|-----------|--------------|---------|
| **Заказы** | Ежедневные, еженедельные, месячные | Excel, PDF, CSV |
| **Товары** | Остатки, продажи, популярные | Excel, PDF |
| **Пользователи** | Регистрации, активность | Excel, CSV |
| **Финансы** | Выручка, платежи | Excel, PDF |
| **Поставщики** | Эффективность, товары | Excel, JSON |

### Создание отчета

Для генерации отчета отправьте POST-запрос с параметрами:

```bash
POST /api/reports/
{
    "report_type": "orders_monthly",
    "format": "excel",
    "parameters": {
        "date_from": "2024-01-01",
        "date_to": "2024-01-31",
        "store_id": 1
    }
}
```
### Автоматические отчеты по расписанию
```bash
POST /api/reports/schedules/
{
    "name": "Ежемесячный отчет по продажам",
    "report_type": "orders_monthly",
    "format": "excel",
    "frequency": "monthly",
    "recipients": ["manager@example.com"]
}
```
## 🐳 Docker

### Команды для работы с Docker
```bash
# Сборка и запуск в фоне
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f django

# Остановка контейнеров
docker-compose down

# Остановка с удалением томов
docker-compose down -v

# Перезапуск сервиса
docker-compose restart django

# Выполнение команд в контейнере
docker-compose exec django python manage.py migrate
docker-compose exec django python manage.py createsuperuser
docker-compose exec django python manage.py test

# Подключение к базе данных
docker-compose exec db psql -U postgres -d order_service

# Подключение к Redis
docker-compose exec redis redis-cli
```
### Production запуск
```bash
# Запуск production стека
docker-compose -f docker-compose.prod.yml up -d

# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f
```
## 🤝 Участие в разработке

1.Форкните репозиторий

2.Создайте ветку для фичи (git checkout -b feature/amazing-feature)

3.Зафиксируйте изменения (git commit -m 'Add amazing feature')

4.Отправьте в форк (git push origin feature/amazing-feature)

5.Откройте Pull Request

## 📞 Контакты

- Разработчик: Фурсов Кирилл

- Email: fursov_gogi@mail.ru



<div align="center">
Order Service — сделано с ❤️ для удобного управления заказами
</div>

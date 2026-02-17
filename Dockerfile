
FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .

# Установка Python пакетов
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Копирование всего проекта
COPY . .

# Проверка наличия manage.py (для отладки)
RUN ls -la /app && echo "=== Содержимое /app ==="

# Открытие порта
EXPOSE 8000

# Запуск приложения
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
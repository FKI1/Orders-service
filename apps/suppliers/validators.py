from django.core.exceptions import ValidationError
import re


def validate_company_name(value):
    """
    Валидация названия компании.
    """
    if not value or len(value.strip()) < 2:
        raise ValidationError('Название компании должно содержать минимум 2 символа')
    
    if len(value) > 255:
        raise ValidationError('Название компании не должно превышать 255 символов')
    
    # Проверка на недопустимые символы
    if re.search(r'[<>{}[\]~`]', value):
        raise ValidationError('Название компании содержит недопустимые символы')
    
    return value


def validate_supplier_phone(value):
    """
    Валидация телефона поставщика.
    """
    if not value:
        return value  # Телефон может быть пустым
    
    # Простая проверка формата телефона
    phone_pattern = r'^\+?[0-9]{10,15}$'
    
    # Убираем все нецифровые символы кроме +
    clean_phone = re.sub(r'[^\d+]', '', value)
    
    if not re.match(phone_pattern, clean_phone):
        raise ValidationError('Некорректный формат телефона')
    
    return clean_phone


def validate_supplier_email(value):
    """
    Валидация email поставщика.
    """
    if not value:
        raise ValidationError('Email обязателен для поставщика')
    
    # Проверка формата email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, value):
        raise ValidationError('Некорректный формат email')
    
    return value


def validate_min_order_amount(value):
    """
    Валидация минимальной суммы заказа для поставщика.
    """
    if value < 0:
        raise ValidationError('Минимальная сумма заказа не может быть отрицательной')
    
    if value > 1000000:  # 1 миллион
        raise ValidationError('Минимальная сумма заказа слишком высока')
    
    return value


def validate_delivery_time(value):
    """
    Валидация времени доставки поставщика.
    """
    if value < 0:
        raise ValidationError('Время доставки не может быть отрицательным')
    
    if value > 365:  # Максимум год на доставку
        raise ValidationError('Время доставки слишком большое')
    
    return value

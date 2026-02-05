import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_tax_id(value):
    """
    Валидация ИНН (российского налогового идентификатора).
    """
    if not value:
        return value
    
    # Проверяем длину (10 или 12 цифр для России)
    if not re.match(r'^\d{10}$', value) and not re.match(r'^\d{12}$', value):
        raise ValidationError(_('ИНН должен содержать 10 или 12 цифр'))
    
    # Проверка контрольной суммы для 10-значного ИНН
    if len(value) == 10:
        coefficients = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        checksum = sum(int(value[i]) * coefficients[i] for i in range(9)) % 11 % 10
        if int(value[9]) != checksum:
            raise ValidationError(_('Некорректный ИНН'))
    
    # Проверка контрольной суммы для 12-значного ИНН
    elif len(value) == 12:
        # Первая контрольная цифра
        coefficients1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        checksum1 = sum(int(value[i]) * coefficients1[i] for i in range(10)) % 11 % 10
        
        # Вторая контрольная цифра
        coefficients2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        checksum2 = sum(int(value[i]) * coefficients2[i] for i in range(11)) % 11 % 10
        
        if int(value[10]) != checksum1 or int(value[11]) != checksum2:
            raise ValidationError(_('Некорректный ИНН'))
    
    return value


def validate_store_code(value):
    """
    Валидация кода магазина.
    """
    if not value:
        raise ValidationError(_('Код магазина обязателен'))
    
    # Код должен содержать только буквы, цифры и дефисы
    if not re.match(r'^[A-Za-z0-9\-_]+$', value):
        raise ValidationError(_('Код магазина может содержать только буквы, цифры, дефисы и подчеркивания'))
    
    # Длина кода
    if len(value) < 2 or len(value) > 50:
        raise ValidationError(_('Код магазина должен быть от 2 до 50 символов'))
    
    return value


def validate_coordinates(latitude, longitude):
    """
    Валидация географических координат.
    """
    if latitude is not None and longitude is not None:
        if not (-90 <= float(latitude) <= 90):
            raise ValidationError(_('Широта должна быть в диапазоне от -90 до 90'))
        
        if not (-180 <= float(longitude) <= 180):
            raise ValidationError(_('Долгота должна быть в диапазоне от -180 до 180'))
    
    return True


def validate_opening_hours(value):
    """
    Валидация часов работы.
    """
    if not value:
        return value
    
    # Простая проверка формата
    # Пример: "Пн-Пт: 9:00-21:00, Сб-Вс: 10:00-20:00"
    lines = value.split(',')
    
    for line in lines:
        line = line.strip()
        if ':' not in line:
            raise ValidationError(_('Некорректный формат часов работы. Используйте: "Дни: время-время"'))
        
        days_part, time_part = line.split(':', 1)
        time_part = time_part.strip()
        
        if '-' not in time_part:
            raise ValidationError(_('Некорректный формат времени. Используйте: "время-время"'))
    
    return value


def validate_phone(value):
    """
    Валидация телефонного номера.
    """
    if not value:
        return value
    
    # Убираем все нецифровые символы кроме +
    clean_phone = re.sub(r'[^\d+]', '', value)
    
    # Проверяем минимальную длину
    if len(clean_phone) < 10:
        raise ValidationError(_('Телефонный номер слишком короткий'))
    
    # Проверяем максимальную длину
    if len(clean_phone) > 15:
        raise ValidationError(_('Телефонный номер слишком длинный'))
    
    # Проверяем, что номер начинается с + или 7 или 8
    if not re.match(r'^(\+?7|8|\+?\d{1,3})', clean_phone):
        raise ValidationError(_('Некорректный формат телефонного номера'))
    
    return clean_phone

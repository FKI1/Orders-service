def create_user_with_profile(email, password, role, phone):
    """Создает пользователя с профилем"""
    user = User.objects.create_user(
        email=email,
        password=password,
        role=role,
        phone=phone
    )
    # Дополнительная логика...
    return user

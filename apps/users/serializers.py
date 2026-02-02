from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User  # Какая модель
        fields = ['id', 'email', 'role', 'phone']  # Какие поля в JSON

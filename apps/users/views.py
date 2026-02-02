from rest_framework.views import APIView
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer

class UserProfileView(APIView):
    def get(self, request):
        user = request.user  # Текущий авторизованный пользователь
        serializer = UserSerializer(user)  # Преобразуем в JSON
        return Response(serializer.data)  # Отправляем клиенту

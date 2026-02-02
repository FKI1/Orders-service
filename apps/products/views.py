from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from .filters import ProductFilter

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'sku', 'description']
    ordering_fields = ['price', 'created_at']

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(parent=None)
    serializer_class = CategorySerializer

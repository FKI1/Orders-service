from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Cart, CartItem
from .serializers import (
    CartSerializer, 
    CartItemSerializer, 
    AddToCartSerializer,
    UpdateCartItemSerializer
)
from apps.products.models import Product

class CartViewSet(viewsets.ViewSet):
    """
    ViewSet для работы с корзиной.
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """
        GET /api/cart/
        Получить содержимое корзины текущего пользователя.
        """
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """
        POST /api/cart/clear/
        Очистить корзину.
        """
        cart = get_object_or_404(Cart, user=request.user)
        cart.clear()
        return Response(
            {'message': 'Корзина очищена'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    def set_store(self, request):
        """
        POST /api/cart/set-store/
        Установить магазин для корзины.
        """
        cart = get_object_or_404(Cart, user=request.user)
        store_id = request.data.get('store_id')
        
        cart.store_id = store_id
        cart.save()
        
        return Response(
            {'message': f'Магазин установлен', 'store_id': store_id},
            status=status.HTTP_200_OK
        )


class CartItemViewSet(viewsets.ViewSet):
    """
    ViewSet для работы с товарами в корзине.
    """
    permission_classes = [IsAuthenticated]
    
    def create(self, request):
        """
        POST /api/cart/items/
        Добавить товар в корзину.
        """
        serializer = AddToCartSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        cart, _ = Cart.objects.get_or_create(user=request.user)
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']
        
        # Проверяем минимальное количество
        if quantity < product.min_order_quantity:
            quantity = product.min_order_quantity
        
        # Создаем или обновляем товар в корзине
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            # Если товар уже есть, увеличиваем количество
            cart_item.quantity += quantity
            cart_item.save()
        
        item_serializer = CartItemSerializer(cart_item)
        return Response(
            item_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    
    def update(self, request, pk=None):
        """
        PUT /api/cart/items/{id}/
        Обновить количество товара в корзине.
        """
        cart_item = get_object_or_404(
            CartItem, 
            pk=pk, 
            cart__user=request.user  # Только свои товары
        )
        
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        quantity = serializer.validated_data['quantity']
        
        # Проверяем минимальное количество
        if quantity < cart_item.product.min_order_quantity:
            return Response(
                {'error': f'Минимальное количество: {cart_item.product.min_order_quantity}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart_item.quantity = quantity
        cart_item.save()
        
        return Response(CartItemSerializer(cart_item).data)
    
    def destroy(self, request, pk=None):
        """
        DELETE /api/cart/items/{id}/
        Удалить товар из корзины.
        """
        cart_item = get_object_or_404(
            CartItem, 
            pk=pk, 
            cart__user=request.user
        )
        cart_item.delete()
        
        return Response(
            {'message': 'Товар удален из корзины'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=['post'])
    def batch_update(self, request):
        """
        POST /api/cart/items/batch-update/
        Массовое обновление товаров в корзине.
        Пример запроса:
        {
            "items": [
                {"product_id": 1, "quantity": 10},
                {"product_id": 2, "quantity": 5}
            ]
        }
        """
        items_data = request.data.get('items', [])
        cart, _ = Cart.objects.get_or_create(user=request.user)
        
        results = []
        errors = []
        
        for item_data in items_data:
            try:
                product_id = item_data.get('product_id')
                quantity = item_data.get('quantity', 1)
                
                product = Product.objects.get(id=product_id)
                
                if quantity < product.min_order_quantity:
                    errors.append({
                        'product_id': product_id,
                        'error': f'Минимальное количество: {product.min_order_quantity}'
                    })
                    continue
                
                cart_item, created = CartItem.objects.update_or_create(
                    cart=cart,
                    product=product,
                    defaults={'quantity': quantity}
                )
                
                results.append({
                    'product_id': product_id,
                    'quantity': quantity,
                    'created': created
                })
                
            except Product.DoesNotExist:
                errors.append({
                    'product_id': product_id,
                    'error': 'Товар не найден'
                })
        
        return Response({
            'updated': results,
            'errors': errors
        })

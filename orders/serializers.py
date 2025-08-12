from rest_framework import serializers
from .models import Order, OrderItem
from products.serializers import ProductSerializer  # Предполагается, что ProductSerializer существует

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price']
        read_only_fields = ['product', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'created_at', 'total', 'items']
        read_only_fields = ['id', 'user', 'created_at', 'total', 'items']

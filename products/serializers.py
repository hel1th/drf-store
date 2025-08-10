from decimal import Decimal
from rest_framework import serializers

from products.models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "description", "stock", "price"]

    def validate_price(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Price must be grater than 0.")
        return value

    def validate_stock(self, value: int):
        if value < 0:
            raise serializers.ValidationError("Stock must be positive.")
        return value

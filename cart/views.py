from .models import CartItem
from .serializers import CartAddSerializer, CartUpdateSerializer, CartItemSerializer
from .services import add_or_update_cart, remove_from_cart, get_cart, remove_product_from_cart
from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class CartItemAddView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CartAddSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            cart_item = add_or_update_cart(
                user=self.request.user,
                product_id=serializer.validated_data["product_id"],
                quantity=serializer.validated_data["quantity"],
            )
            return Response(
                CartItemSerializer(cart_item).data, status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CartItemUpdateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CartUpdateSerializer

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_id = serializer.validated_data["product_id"]
        quantity = serializer.validated_data["quantity"]

        if quantity == 0:
            remove_from_cart(user=self.request.user, product_id=product_id)
            return Response(status=status.HTTP_204_NO_CONTENT)

        try:
            cart_item = add_or_update_cart(
                user=self.request.user, product_id=product_id, quantity=quantity
            )
            return Response(
                CartItemSerializer(cart_item).data, status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CartItemRemoveView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, product_id):
        success = remove_product_from_cart(request.user, product_id)
        if not success:
            return Response({"detail": "Item not found in cart"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartListView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CartItemSerializer

    def get(self, request, *args, **kwargs):
        cart_items = get_cart(user=self.request.user)
        serializer = self.get_serializer(cart_items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

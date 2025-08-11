from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from .services import create_order_from_cart
from .serializers import OrderSerializer


class OrderCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def post(self, request):
        try:
            order = create_order_from_cart(request.user)
        except ValidationError as e:
            return Response({"details": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
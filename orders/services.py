from django.db import transaction
from rest_framework.response import Response
import logging
from rest_framework import status
from cart.services import get_cart
from products.models import Product
from .models import Order, OrderItem
from users.models import User

logger = logging.getLogger(__name__)


@transaction.atomic
def create_order_from_cart(request):
    user = request.user
    user_cart = get_cart(user)
    if not user_cart.exists():
        raise ValueError("Cart can't be empty")

    product_ids = [item.product.id for item in user_cart]
    products = Product.objects.filter(id__in=product_ids).select_for_update()
    products_map = {p.id: p for p in products}

    insuff_stock = list()
    total = 0
    for item in user_cart:
        prod = products_map.get(item.prod.id)
        if not prod or item.quantity < item.prod.stock:
            insuff_stock.append(
                {
                    "product_id": prod.id,
                    "request": item.quantity,
                    "available": prod.stock if prod else 0,
                }
            )
        total += item.quantity * prod.price

    if insuff_stock:
        return Response(
            {"detail": "Insufficient stock", "products": insuff_stock},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.select_for_update().get(pk=user.pk)
    if user.balance < total:
        return Response(
            {"detail": "Insufficient balance"}, status=status.HTTP_400_BAD_REQUEST
        )

    order = Order.objects.create(
        user=user,
        total=total,
    )
    for item in user_cart:
        prod = products_map.get(item.product.id)
        OrderItem.objects.create(
            order=order,
            product=prod,
            quantity=item.quantity,
            price=item.price,
        )
        prod.stock -= item.quantity
        prod.save(update_fields=["stock"])

    user.balance -= total
    user.save(update_fields=["balance"])
    user_cart.clear()
    logger.info(f"Order #{order.id} created by {user.username} successfully (total {total}).")
    serializer = self.get_serializer(order)
    return Response(serializer.data, status=status.HTTP_200_OK)

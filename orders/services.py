from django.db import transaction
from rest_framework.exceptions import ValidationError
import logging
from cart.services import get_cart
from products.models import Product
from .models import Order, OrderItem
from users.models import User

logger = logging.getLogger(__name__)

@transaction.atomic
def create_order_from_cart(user):
    user_cart = get_cart(user)

    if not user_cart.exists():
        raise ValidationError({"detail": ["Cart can't be empty"]})


    product_ids = [item.product.id for item in user_cart]
    products = Product.objects.filter(id__in=product_ids).select_for_update()
    products_map = {p.id: p for p in products}

    insuff_stock = []
    total = 0

    for item in user_cart:
        prod = products_map.get(item.product.id)

        if not prod or item.quantity > prod.stock:
            insuff_stock.append({
                "product_id": prod.id if prod else item.product.id,
                "requested": item.quantity,
                "available": prod.stock if prod else 0,
            })
            continue

        total += item.quantity * prod.price

    if insuff_stock:
        raise ValidationError({
            "detail": "Insufficient stock",
            "products": insuff_stock
        })

    locked_user = User.objects.select_for_update().get(pk=user.pk)
    if locked_user.balance < total:
        raise ValidationError({"detail": f"Insufficient balance {total - locked_user.balance} more needed"})

    order = Order.objects.create(
        user=locked_user,
        total=total,
    )

    for item in user_cart:
        prod = products_map.get(item.product.id)
        if not prod or item.quantity > prod.stock:
            continue
        OrderItem.objects.create(
            order=order,
            product=prod,
            quantity=item.quantity,
            price=prod.price,
        )
        prod.stock -= item.quantity
        prod.save(update_fields=["stock"])

    locked_user.balance -= total
    locked_user.save(update_fields=["balance"])


    user_cart.delete()

    logger.info(
        f"Order #{order.id} created by {locked_user.username} successfully (total {total})."
    )
    return order

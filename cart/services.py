from .models import CartItem
from django.db.models import ObjectDoesNotExist

def remove_from_cart(user, product_id):
    CartItem.objects.filter(user=user, product_id=product_id).delete()


def get_cart(user):
    return CartItem.objects.filter(user=user).select_related("product")


def remove_product_from_cart(user, product_id):
    try:
        cart_item = CartItem.objects.get(user=user, product_id=product_id)
        cart_item.delete()
        return True
    except ObjectDoesNotExist:
        return False

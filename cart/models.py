from django.db import models, transaction
from django.forms import ValidationError

from products.models import Product
from users.models import User


# Create your models here.
class CartItemManager(models.Manager):
    @transaction.atomic
    def add(self, user, product_id, quantity, update=False):
        product = Product.objects.select_for_update().get(pk=product_id)
        item, _ = self.select_for_update().get_or_create(user=user, product=product)

        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")

        if not update:
            new_amount = item.quantity + quantity
            if new_amount > product.stock:
                raise ValidationError("Not enough stock.")
            item.quantity = new_amount
        else:
            if quantity > product.stock:
                raise ValidationError("Not enough stock.")
            item.quantity = quantity

        item.save()
        return item


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    objects = CartItemManager()

    class Meta:
        unique_together = ("user", "product")

    def __str__(self):
        return f"{self.user} — {self.product.name} x{self.quantity}"

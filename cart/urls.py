from django.urls import path
from .views import CartItemAddView, CartItemUpdateView, CartItemRemoveView, CartListView

urlpatterns = [
    path("add/", CartItemAddView.as_view(), name="cart-add"),
    path("update/", CartItemUpdateView.as_view(), name="cart-update"),
    path("remove/<int:product_id>", CartItemRemoveView.as_view(), name="cart-remove"),
    path("", CartListView.as_view(), name="cart-list"),
]

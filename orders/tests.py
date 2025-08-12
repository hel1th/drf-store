import uuid
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.urls import reverse
from users.models import User
from products.models import Product
from cart.models import CartItem
from orders.models import Order, OrderItem
from orders.services import create_order_from_cart
from orders.serializers import OrderSerializer, OrderItemSerializer


class OrderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}",
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password="password123",
            balance=Decimal("100.00"),
        )

    def test_create_order(self):
        order = Order.objects.create(user=self.user, total=Decimal("20.00"))
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.total, Decimal("20.00"))
        self.assertIsNotNone(order.created_at)

    def test_str_method(self):
        order = Order.objects.create(user=self.user, total=Decimal("20.00"))
        self.assertEqual(str(order), f"Order #{order.id}")


class OrderItemModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}",
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password="password123",
            balance=Decimal("100.00"),
        )
        self.product = Product.objects.create(
            name="Test Product",
            price=Decimal("10.00"),
            stock=10,
            description="Test description",
        )
        self.order = Order.objects.create(user=self.user, total=Decimal("20.00"))

    def test_create_order_item(self):
        order_item = OrderItem.objects.create(
            order=self.order, product=self.product, quantity=2, price=Decimal("10.00")
        )
        self.assertEqual(order_item.order, self.order)
        self.assertEqual(order_item.product, self.product)
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.price, Decimal("10.00"))

    def test_str_method(self):
        order_item = OrderItem.objects.create(
            order=self.order, product=self.product, quantity=2, price=Decimal("10.00")
        )
        self.assertEqual(str(order_item), f"OrderItem #{order_item.id}")


class OrderSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}",
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password="password123",
            balance=Decimal("100.00"),
        )
        self.product = Product.objects.create(
            name="Test Product",
            price=Decimal("10.00"),
            stock=10,
            description="Test description",
        )
        self.order = Order.objects.create(user=self.user, total=Decimal("20.00"))
        self.order_item = OrderItem.objects.create(
            order=self.order, product=self.product, quantity=2, price=Decimal("10.00")
        )

    def test_order_serializer(self):
        serializer = OrderSerializer(self.order)
        expected_data = {
            "id": self.order.id,
            "user": self.user.id,
            "created_at": serializer.data["created_at"],
            "total": "20.00",
            "items": [
                {
                    "product": {
                        "id": self.product.id,
                        "name": self.product.name,
                        "price": "10.00",
                        "stock": self.product.stock,
                        "description": self.product.description,
                    },
                    "quantity": 2,
                    "price": "10.00",
                }
            ],
        }
        self.assertEqual(serializer.data, expected_data)

    def test_order_serializer_ignores_read_only_fields(self):
        order = Order.objects.create(user=self.user, total=Decimal("20.00"))
        data = {
            "id": 999,
            "user": 999,
            "created_at": "2025-08-12T12:00:00Z",
            "total": "100.00",
            "items": [],
        }
        serializer = OrderSerializer(instance=order, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {})


class OrderItemSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}",
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password="password123",
            balance=Decimal("100.00"),
        )
        self.product = Product.objects.create(
            name="Test Product",
            price=Decimal("10.00"),
            stock=10,
            description="Test description",
        )
        self.order = Order.objects.create(user=self.user, total=Decimal("20.00"))
        self.order_item = OrderItem.objects.create(
            order=self.order, product=self.product, quantity=2, price=Decimal("10.00")
        )

    def test_order_item_serializer(self):
        serializer = OrderItemSerializer(self.order_item)
        expected_data = {
            "product": {
                "id": self.product.id,
                "name": self.product.name,
                "price": "10.00",
                "stock": self.product.stock,
                "description": self.product.description,
            },
            "quantity": 2,
            "price": "10.00",
        }
        self.assertEqual(serializer.data, expected_data)


class CreateOrderFromCartTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:8]}',
            email=f'test_{uuid.uuid4().hex[:8]}@example.com',
            password='password123',
            balance=Decimal("100.00"),
        )
        self.product = Product.objects.create(
            name="Test Product", price=Decimal("10.00"), stock=5
        )

    def test_insufficient_stock_raises(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=10)
        with self.assertRaises(ValidationError) as ctx:
            create_order_from_cart(self.user)
        self.assertEqual(ctx.exception.detail['detail'], "Insufficient stock")
        self.assertIn('products', ctx.exception.detail)
        self.assertEqual(len(ctx.exception.detail['products']), 1)
        insuff_product = ctx.exception.detail['products'][0]
        self.assertEqual(int(insuff_product['product_id']), self.product.id)
        self.assertEqual(int(insuff_product['requested']), 10)
        self.assertEqual(int(insuff_product['available']), 5)

    def test_empty_cart_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            create_order_from_cart(self.user)

        self.assertIn(
            "Cart can't be empty",
            ctx.exception.detail.get("detail", [])
        )

    def test_insufficient_balance_raises(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=4)
        self.user.balance = Decimal("30.00")
        self.user.save()
        with self.assertRaises(ValidationError) as ctx:
            create_order_from_cart(self.user)

        self.assertIn("Insufficient balance", ctx.exception.detail.get("detail", []))
        self.assertIn("10.00 more needed", ctx.exception.detail.get("detail", []))

    def test_successful_order(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=2)
        order = create_order_from_cart(self.user)

        self.assertIsInstance(order, Order)
        self.assertEqual(order.total, Decimal("20.00"))

        items = OrderItem.objects.filter(order=order)
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first().quantity, 2)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("80.00"))

        self.assertFalse(CartItem.objects.filter(user=self.user).exists())

    def test_successful_order_with_multiple_items(self):
        product2 = Product.objects.create(
            name="Test Product 2", price=Decimal("15.00"), stock=3
        )
        CartItem.objects.create(user=self.user, product=self.product, quantity=2)
        CartItem.objects.create(user=self.user, product=product2, quantity=1)

        order = create_order_from_cart(self.user)

        self.assertEqual(order.total, Decimal("35.00"))

        items = OrderItem.objects.filter(order=order)
        self.assertEqual(items.count(), 2)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

        product2.refresh_from_db()
        self.assertEqual(product2.stock, 2)

        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("65.00"))

        self.assertFalse(CartItem.objects.filter(user=self.user).exists())


class OrderCreateViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("create-order")
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}",
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password="password123",
            balance=Decimal("100.00"),
        )
        self.product = Product.objects.create(
            name="Test Product", price=Decimal("10.00"), stock=5, description="Test description"
        )

    def auth(self):
        response = self.client.post(
            "/api/user/token/",
            {"username": self.user.username, "password": "password123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])

    def test_unauthenticated_user_cannot_create_order(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_cart_returns_400(self):
        self.auth()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cart can't be empty", str(response.data))

    def test_insufficient_stock_returns_400(self):
        self.auth()
        CartItem.objects.create(user=self.user, product=self.product, quantity=10)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient stock", str(response.data))
        self.assertIn("products", response.data)

    def test_insufficient_balance_returns_400(self):
        self.auth()
        CartItem.objects.create(user=self.user, product=self.product, quantity=4)
        self.user.balance = Decimal("30.00")
        self.user.save()

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient balance", str(response.data))

    def test_successful_order_creation(self):
        self.auth()
        CartItem.objects.create(user=self.user, product=self.product, quantity=2)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order_id = response.data["id"]
        order = Order.objects.get(id=order_id)

        self.assertEqual(order.total, Decimal("20.00"))
        self.assertEqual(order.user, self.user)

        items = OrderItem.objects.filter(order=order)
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first().quantity, 2)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("80.00"))

        expected_data = {
            "id": order.id,
            "user": self.user.id,
            "created_at": response.data["created_at"],
            "total": "20.00",
            "items": [
                {
                    "product": {
                        "id": self.product.id,
                        "name": self.product.name,
                        "price": "10.00",
                        "stock": self.product.stock,
                        "description": self.product.description,
                    },
                    "quantity": 2,
                    "price": "10.00",
                }
            ],
        }
        self.assertEqual(response.data, expected_data)

    def test_successful_order_creation_multiple_items(self):
        self.auth()
        product2 = Product.objects.create(
            name="Test Product 2", price=Decimal("15.00"), stock=3, description="Test description 2"
        )
        CartItem.objects.create(user=self.user, product=self.product, quantity=2)
        CartItem.objects.create(user=self.user, product=product2, quantity=1)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order_id = response.data["id"]
        order = Order.objects.get(id=order_id)

        self.assertEqual(order.total, Decimal("35.00"))

        items = OrderItem.objects.filter(order=order)
        self.assertEqual(items.count(), 2)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

        product2.refresh_from_db()
        self.assertEqual(product2.stock, 2)

        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("65.00"))

        expected_data = {
            "id": order.id,
            "user": self.user.id,
            "created_at": response.data["created_at"],
            "total": "35.00",
            "items": [
                {
                    "product": {
                        "id": self.product.id,
                        "name": self.product.name,
                        "price": "10.00",
                        "stock": self.product.stock,
                        "description": self.product.description,
                    },
                    "quantity": 2,
                    "price": "10.00",
                },
                {
                    "product": {
                        "id": product2.id,
                        "name": product2.name,
                        "price": "15.00",
                        "stock": product2.stock,
                        "description": product2.description,
                    },
                    "quantity": 1,
                    "price": "15.00",
                },
            ],
        }
        self.assertEqual(response.data, expected_data)

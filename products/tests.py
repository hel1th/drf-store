import uuid
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from products.models import Product
from products.serializers import ProductSerializer
from users.models import User


class PrductModelTests(TestCase):
    def test_create_product(self):
        product = Product.objects.create(
            name="Test Product",
            description="Test Description",
            price=Decimal("15.01"),
            stock=100,
        )
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.description, "Test Description")
        self.assertEqual(product.price, Decimal("15.01"))
        self.assertEqual(product.stock, 100)

    def test_str_method(self):
        product = Product.objects.create(
            name="Test Product", price=Decimal("15.01"), stock=50
        )
        self.assertEqual(str(product), "Test Product (price: 15.01)")


class ProductSerializerTest(TestCase):
    def test_valid_data(self):
        data = {
            "name": "Test Product",
            "description": "A test product",
            "price": "10.00",
            "stock": 100,
        }
        serializer = ProductSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        product = serializer.save()
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.price, Decimal("10.00"))
        self.assertEqual(product.stock, 100)

    def test_negative_price(self):
        data = {
            "name": "Test Product",
            "description": "A test product",
            "price": "-10.00",
            "stock": 100,
        }
        serializer = ProductSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("price", serializer.errors)
        self.assertEqual(serializer.errors["price"][0], "Price must be greater than 0.")

    def test_negative_stock(self):
        data = {
            "name": "Test Product",
            "description": "A test product",
            "price": "10.00",
            "stock": -5,
        }
        serializer = ProductSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("stock", serializer.errors)
        self.assertEqual(
            serializer.errors["stock"][0],
            "Ensure this value is greater than or equal to 0.",
        )

    def test_zero_price(self):
        data = {
            "name": "Test Product",
            "description": "A test product",
            "price": "0.00",
            "stock": 100,
        }
        serializer = ProductSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("price", serializer.errors)


class ProductListCreateViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}",
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password="password123",
        )
        self.admin = User.objects.create_superuser(
            username=f"admin_{uuid.uuid4().hex[:8]}",
            email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
            password="admin123",
        )
        response = self.client.post(
            "/api/user/token/",
            {"username": self.admin.username, "password": "admin123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content)
        self.admin_token = response.data["access"]

        self.product = Product.objects.create(
            name="Test Product",
            description="A test product",
            price=Decimal("10.00"),
            stock=100,
        )

    def test_list_products_unauthenticated(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Test Product")

    def test_create_product_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.admin_token)
        data = {
            "name": "New Product",
            "description": "A new product",
            "price": "20.00",
            "stock": 50,
        }
        response = self.client.post("/api/products/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)
        self.assertEqual(Product.objects.last().name, "New Product")

    def test_create_product_non_admin(self):
        response = self.client.post(
            "/api/user/token/",
            {"username": self.user.username, "password": "password123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + user_token)
        data = {
            "name": "New Product",
            "description": "A new product",
            "price": "20.00",
            "stock": 50,
        }
        response = self.client.post("/api/products/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_product_unauthenticated(self):
        self.client.credentials()
        data = {
            "name": "New Product",
            "description": "A new product",
            "price": "20.00",
            "stock": 50,
        }
        response = self.client.post("/api/products/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProductDetailViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}",
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password="password123",
        )
        self.admin = User.objects.create_superuser(
            username=f"admin_{uuid.uuid4().hex[:8]}",
            email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
            password="admin123",
        )
        response = self.client.post(
            "/api/user/token/",
            {"username": self.admin.username, "password": "admin123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content)
        self.admin_token = response.data["access"]
        self.product = Product.objects.create(
            name="Test Product",
            description="A test product",
            price=Decimal("10.00"),
            stock=100,
        )

    def test_retrieve_product_unauthenticated(self):
        response = self.client.get(f"/api/products/{self.product.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Product")
        self.assertEqual(response.data["price"], "10.00")

    def test_update_product_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.admin_token)
        data = {
            "name": "Updated Product",
            "description": "Updated description",
            "price": "15.00",
            "stock": 200,
        }
        response = self.client.put(
            f"/api/products/{self.product.id}/", data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Updated Product")
        self.assertEqual(self.product.price, Decimal("15.00"))
        self.assertEqual(self.product.stock, 200)

    def test_update_product_non_admin(self):
        response = self.client.post(
            "/api/user/token/",
            {"username": self.user.username, "password": "password123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + user_token)
        data = {
            "name": "Updated Product",
            "description": "Updated description",
            "price": "15.00",
            "stock": 200,
        }
        response = self.client.put(
            f"/api/products/{self.product.id}/", data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_product_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.admin_token)
        response = self.client.delete(f"/api/products/{self.product.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())

    def test_delete_product_non_admin(self):
        response = self.client.post(
            "/api/user/token/",
            {"username": self.user.username, "password": "password123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + user_token)
        response = self.client.delete(f"/api/products/{self.product.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_product_unauthenticated(self):
        self.client.credentials()
        response = self.client.delete(f"/api/products/{self.product.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

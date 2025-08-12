from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
from .models import User
from .serializers import RegisterSerializer, DepositSerializer, UserProfileSerializer


class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            username="test",
            email="test@test.com",
            password="testpswd1234",
        )
        self.assertEqual(user.username, "test")
        self.assertEqual(user.email, "test@test.com")
        self.assertTrue(user.check_password("testpswd1234"))

    def test_str_user(self):
        user = User.objects.create_user(
            username="test",
            email="test@test.com",
            password="testpswd1234",
        )
        self.assertEqual(str(user), "User: test email: test@test.com")


class RegisterSerializerTest(TestCase):
    def setUp(self):
        self.old_user = User.objects.create_user(
            username="test",
            email="test@test.com",
            password="somepswd1234",
        )

    def test_valid_data(self):
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.username, "newuser")
        self.assertEqual(user.email, "newuser@example.com")
        self.assertTrue(user.check_password("password123"))

    def test_duplicate_username(self):
        data = {
            "username": "test",
            "email": "new_mail@test.com",
            "password": "somepswd1234",
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid(), serializer.errors)
        self.assertIn("username", serializer.errors)

    def test_duplicate_email(self):
        data = {
            "username": "test_new",
            "email": "test@test.com",
            "password": "somepswd1234",
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid(), serializer.errors)
        self.assertIn("email", serializer.errors)

    def test_blank_fields(self):
        serializer = RegisterSerializer(
            data={"username": "", "email": "", "password": ""}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)
        self.assertIn("username", serializer.errors)
        self.assertIn("email", serializer.errors)


class DepositSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test",
            email="test@test.com",
            password="123PASSWORD",
        )

    def test_valid_amount(self):
        data = {"amount": "25.01"}
        serializer = DepositSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertTrue(serializer.validated_data["amount"], Decimal("25.01"))

    def test_zero_amount(self):
        data = {"amount": "0.00"}
        serializer = DepositSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)

    def test_negative_amount(self):
        data = {"amount": "-24.42"}
        serializer = DepositSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)


class RegisterViewTest(APITestCase):
    def test_register_success(self):
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
        }
        response = self.client.post("/api/user/register/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_duplicate_email(self):
        User.objects.create_user(
            username="existing", email="duplicate@example.com", password="password123"
        )
        data = {
            "username": "newuser",
            "email": "duplicate@example.com",
            "password": "password123",
        }
        response = self.client.post("/api/user/register/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProfileViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser111",
            email="test12341@example.com",
            password="password123",
            balance="100.00",
        )
        response = self.client.post(
            "/api/user/token/",
            {"username": "testuser111", "password": "password123"},
            format="json",
        )
        self.token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_get_profile(self):
        response = self.client.get(path="/api/user/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.user.username)
        self.assertEqual(response.data["balance"], self.user.balance)

    def test_unauthenticated(self):
        self.client.credentials()
        response = self.client.get(
            path="/api/user/profile/",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class DepositViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            balance="100.00",
        )
        response = self.client.post(
            "/api/user/token/",
            {"username": "testuser", "password": "password123"},
            format="json",
        )
        self.token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.token)

    def test_deposit_success(self):
        data = {"amount": "50.00"}
        response = self.client.post("/api/user/balance/deposit/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("150.00"))
        self.assertEqual(response.data["balance"], "150.00")

    def test_invalid_amount(self):
        data = {"amount": "-10.00"}
        response = self.client.post("/api/user/balance/deposit/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated(self):
        self.client.credentials()
        data = {"amount": "50.00"}
        response = self.client.post("/api/user/balance/deposit/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

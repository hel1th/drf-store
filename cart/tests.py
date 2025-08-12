import uuid
from decimal import Decimal
from django.test import TestCase
from django.db.utils import IntegrityError
from rest_framework.test import APITestCase
from rest_framework import status
from django.core.exceptions import ValidationError
from users.models import User
from products.models import Product
from cart.models import CartItem
from cart.serializers import CartItemSerializer, CartAddSerializer, CartUpdateSerializer
from cart.services import remove_from_cart, get_cart, remove_product_from_cart

class CartItemModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:8]}',
            email=f'test_{uuid.uuid4().hex[:8]}@example.com',
            password='password123'
        )
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('10.00'),
            stock=100
        )

    def test_create_cart_item(self):
        cart_item = CartItem.objects.create(
            user=self.user,
            product=self.product,
            quantity=5
        )
        self.assertEqual(cart_item.user, self.user)
        self.assertEqual(cart_item.product, self.product)
        self.assertEqual(cart_item.quantity, 5)

    def test_str_method(self):
        cart_item = CartItem.objects.create(
            user=self.user,
            product=self.product,
            quantity=3
        )
        self.assertEqual(str(cart_item), f"{self.user} — {self.product.name} x 3")

    def test_unique_together(self):
        CartItem.objects.create(
            user=self.user,
            product=self.product,
            quantity=2
        )
        with self.assertRaises(IntegrityError):
            CartItem.objects.create(
                user=self.user,
                product=self.product,
                quantity=3
            )

class CartItemManagerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:8]}',
            email=f'test_{uuid.uuid4().hex[:8]}@example.com',
            password='password123'
        )
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('10.00'),
            stock=10
        )

    def test_add_new_item(self):
        cart_item = CartItem.objects.add(
            user=self.user,
            product_id=self.product.id,
            quantity=5
        )
        self.assertEqual(cart_item.quantity, 5)
        self.assertEqual(cart_item.user, self.user)
        self.assertEqual(cart_item.product, self.product)

    def test_add_existing_item(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=3)
        cart_item = CartItem.objects.add(
            user=self.user,
            product_id=self.product.id,
            quantity=4
        )
        self.assertEqual(cart_item.quantity, 7)

    def test_add_exceed_stock(self):
        with self.assertRaises(ValidationError) as cm:
            CartItem.objects.add(
                user=self.user,
                product_id=self.product.id,
                quantity=15
            )
        self.assertEqual(str(cm.exception), "['Not enough stock.']")

    def test_update_quantity(self):
        cart_item = CartItem.objects.create(user=self.user, product=self.product, quantity=3)
        updated_item = CartItem.objects.update(
            user=self.user,
            product_id=self.product.id,
            quantity=5
        )
        self.assertEqual(updated_item.quantity, 5)

    def test_update_exceed_stock(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=3)
        with self.assertRaises(ValidationError) as cm:
            CartItem.objects.update(
                user=self.user,
                product_id=self.product.id,
                quantity=15
            )
        self.assertEqual(str(cm.exception), "['Not enough stock.']")

    def test_add_negative_quantity(self):
        with self.assertRaises(ValidationError) as cm:
            CartItem.objects.add(
                user=self.user,
                product_id=self.product.id,
                quantity=-1
            )
        self.assertEqual(str(cm.exception), "['Quantity must be positive.']")

class CartServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:8]}',
            email=f'test_{uuid.uuid4().hex[:8]}@example.com',
            password='password123'
        )
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('10.00'),
            stock=10
        )

    def test_add_cart(self):
        cart_item = CartItem.objects.add(self.user, self.product.id, 5)
        self.assertEqual(cart_item.quantity, 5)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_update_cart(self):
        cart_item = CartItem.objects.update(self.user, self.product.id, 3)
        self.assertEqual(cart_item.quantity, 3)

    def test_remove_from_cart(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=5)
        remove_from_cart(self.user, self.product.id)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_get_cart(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=5)
        cart_items = get_cart(self.user)
        self.assertEqual(len(cart_items), 1)
        self.assertEqual(cart_items[0].quantity, 5)

    def test_remove_product_from_cart(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=5)
        success = remove_product_from_cart(self.user, self.product.id)
        self.assertTrue(success)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_remove_nonexistent_product(self):
        success = remove_product_from_cart(self.user, 999)
        self.assertFalse(success)

class CartSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:8]}',
            email=f'test_{uuid.uuid4().hex[:8]}@example.com',
            password='password123'
        )
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('10.00'),
            stock=10
        )

    def test_cart_item_serializer(self):
        cart_item = CartItem.objects.create(user=self.user, product=self.product, quantity=5)
        serializer = CartItemSerializer(cart_item)
        expected_data = {
            'id': cart_item.id,
            'product': {
                'id': self.product.id,
                'name': self.product.name,
                'description': self.product.description,
                'price': '10.00',
                'stock': self.product.stock
            },
            'quantity': 5
        }
        self.assertEqual(serializer.data, expected_data)

    def test_cart_add_serializer_valid(self):
        data = {
            'product_id': self.product.id,
            'quantity': 5
        }
        serializer = CartAddSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['product_id'], self.product.id)
        self.assertEqual(serializer.validated_data['quantity'], 5)

    def test_cart_add_serializer_invalid_product(self):
        data = {
            'product_id': 999,
            'quantity': 5
        }
        serializer = CartAddSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('product_id', serializer.errors)
        self.assertEqual(str(serializer.errors['product_id'][0]), 'No such product.')

    def test_cart_add_serializer_negative_quantity(self):
        data = {
            'product_id': self.product.id,
            'quantity': -1
        }
        serializer = CartAddSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('quantity', serializer.errors)
        self.assertEqual(str(serializer.errors['quantity'][0]), 'Ensure this value is greater than or equal to 1.')

    def test_cart_update_serializer_valid(self):
        data = {
            'product_id': self.product.id,
            'quantity': 0
        }
        serializer = CartUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['quantity'], 0)

    def test_cart_update_serializer_negative_quantity(self):
        data = {
            'product_id': self.product.id,
            'quantity': -1
        }
        serializer = CartUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('quantity', serializer.errors)
        self.assertEqual(str(serializer.errors['quantity'][0]), 'Ensure this value is greater than or equal to 0.')

class CartItemAddViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:8]}',
            email=f'test_{uuid.uuid4().hex[:8]}@example.com',
            password='password123'
        )
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('10.00'),
            stock=10
        )
        response = self.client.post('/api/user/token/', {
            'username': self.user.username,
            'password': 'password123'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content)
        self.token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_add_to_cart(self):
        data = {
            'product_id': self.product.id,
            'quantity': 5
        }
        response = self.client.post('/api/cart/add/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(CartItem.objects.first().quantity, 5)

    def test_add_exceed_stock(self):
        data = {
            'product_id': self.product.id,
            'quantity': 15
        }
        response = self.client.post('/api/cart/add/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "['Not enough stock.']")

    def test_add_unauthenticated(self):
        self.client.credentials()
        data = {
            'product_id': self.product.id,
            'quantity': 5
        }
        response = self.client.post('/api/cart/add/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class CartItemUpdateViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:8]}',
            email=f'test_{uuid.uuid4().hex[:8]}@example.com',
            password='password123'
        )
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('10.00'),
            stock=10
        )
        self.cart_item = CartItem.objects.create(
            user=self.user,
            product=self.product,
            quantity=3
        )
        response = self.client.post('/api/user/token/', {
            'username': self.user.username,
            'password': 'password123'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content)
        self.token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_update_cart_item(self):
        data = {
            'product_id': self.product.id,
            'quantity': 5
        }
        response = self.client.patch('/api/cart/update/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.cart_item.refresh_from_db()
        self.assertEqual(self.cart_item.quantity, 5)

    def test_update_to_zero(self):
        data = {
            'product_id': self.product.id,
            'quantity': 0
        }
        response = self.client.patch('/api/cart/update/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_update_exceed_stock(self):
        data = {
            'product_id': self.product.id,
            'quantity': 15
        }
        response = self.client.patch('/api/cart/update/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "['Not enough stock.']")

    def test_update_unauthenticated(self):
        self.client.credentials()
        data = {
            'product_id': self.product.id,
            'quantity': 5
        }
        response = self.client.patch('/api/cart/update/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class CartItemRemoveViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:8]}',
            email=f'test_{uuid.uuid4().hex[:8]}@example.com',
            password='password123'
        )
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('10.00'),
            stock=10
        )
        self.cart_item = CartItem.objects.create(
            user=self.user,
            product=self.product,
            quantity=3
        )
        response = self.client.post('/api/user/token/', {
            'username': self.user.username,
            'password': 'password123'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content)
        self.token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_remove_from_cart(self):
        response = self.client.delete(f'/api/cart/remove/{self.product.id}')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_remove_nonexistent_item(self):
        response = self.client.delete('/api/cart/remove/999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'], 'Item not found in cart')

    def test_remove_unauthenticated(self):
        self.client.credentials()
        response = self.client.delete(f'/api/cart/remove/{self.product.id}')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class CartListViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:8]}',
            email=f'test_{uuid.uuid4().hex[:8]}@example.com',
            password='password123'
        )
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('10.00'),
            stock=10
        )
        self.cart_item = CartItem.objects.create(
            user=self.user,
            product=self.product,
            quantity=3
        )
        response = self.client.post('/api/user/token/', {
            'username': self.user.username,
            'password': 'password123'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content)
        self.token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_list_cart(self):
        response = self.client.get('/api/cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['quantity'], 3)
        self.assertEqual(response.data[0]['product']['id'], self.product.id)

    def test_list_empty_cart(self):
        CartItem.objects.all().delete()
        response = self.client.get('/api/cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_list_unauthenticated(self):
        self.client.credentials()
        response = self.client.get('/api/cart/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

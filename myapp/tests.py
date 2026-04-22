from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from .models import (
    Cloths, Toy, Offers, NewArrivals, Cart, CartItem, Order, OrderItem,
    Inventory, Coupon, WishlistItem, ProductVariant, Review, ContactMessage,
)
from django.utils import timezone
from datetime import timedelta


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@test.com', password='TestPass123!')
        self.cloth = Cloths.objects.create(
            name='Test Shirt', price='1000', price1='1200', price2='1000',
            desccription='A test shirt', category='men'
        )
        self.toy = Toy.objects.create(
            name='Test Toy', description='A test toy', category='educational',
            age_range='3-5', price=Decimal('500'), imageUrl='toys/test.jpg'
        )

    def test_cloth_creation(self):
        self.assertEqual(self.cloth.name, 'Test Shirt')
        self.assertEqual(str(self.cloth), 'Test Shirt')

    def test_toy_creation(self):
        self.assertEqual(self.toy.name, 'Test Toy')
        self.assertEqual(self.toy.price, Decimal('500'))

    def test_toy_discount_percentage(self):
        self.toy.original_price = Decimal('1000')
        self.toy.save()
        self.assertEqual(self.toy.discount_percentage, 50)

    def test_cart_creation(self):
        cart = Cart.objects.create(user=self.user)
        self.assertEqual(str(cart), 'Cart for testuser')
        self.assertEqual(cart.get_total(), 0.0)
        self.assertEqual(cart.get_item_count(), 0)

    def test_cart_item_operations(self):
        cart = Cart.objects.create(user=self.user)
        ci = CartItem.objects.create(cart=cart, item_type='toy', toy=self.toy, quantity=2)
        self.assertEqual(ci.get_price(), 500.0)
        self.assertEqual(ci.get_subtotal(), 1000.0)
        self.assertEqual(cart.get_item_count(), 2)

    def test_order_creation(self):
        order = Order.objects.create(
            user=self.user, order_number='ORD-TEST0001',
            full_name='Test User', email='test@test.com', phone='123',
            address='123 St', city='Colombo', postal_code='10100', country='LK',
            subtotal=Decimal('1000'), tax=Decimal('100'), total=Decimal('1110'),
        )
        self.assertEqual(order.status, 'pending')
        self.assertEqual(str(order), 'Order ORD-TEST0001 - testuser')

    def test_inventory(self):
        inv = Inventory.objects.create(product_type='toy', toy=self.toy, stock=10, low_stock_threshold=5)
        self.assertTrue(inv.is_in_stock)
        self.assertFalse(inv.is_low_stock)
        inv.stock = 3
        inv.save()
        self.assertTrue(inv.is_low_stock)
        inv.stock = 0
        inv.save()
        self.assertFalse(inv.is_in_stock)

    def test_coupon_validity(self):
        coupon = Coupon.objects.create(
            code='TEST20', discount_type='percentage', discount_value=Decimal('20'),
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=30),
            is_active=True,
        )
        self.assertTrue(coupon.is_valid())
        discount = coupon.get_discount(Decimal('1000'))
        self.assertEqual(discount, Decimal('200.00'))

    def test_expired_coupon(self):
        coupon = Coupon.objects.create(
            code='EXPIRED', discount_type='fixed', discount_value=Decimal('100'),
            valid_from=timezone.now() - timedelta(days=30),
            valid_until=timezone.now() - timedelta(days=1),
            is_active=True,
        )
        self.assertFalse(coupon.is_valid())

    def test_wishlist_item(self):
        wi = WishlistItem.objects.create(user=self.user, item_type='cloth', cloth=self.cloth)
        self.assertEqual(wi.get_item(), self.cloth)


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='test@test.com', password='TestPass123!')
        self.cloth = Cloths.objects.create(
            name='View Test Shirt', price='1500', price2='1500',
            desccription='Test', category='men', imageUrl='cloths/test.jpg'
        )
        self.toy = Toy.objects.create(
            name='View Test Toy', description='Test', category='educational',
            age_range='3-5', price=Decimal('750'), imageUrl='toys/test.jpg'
        )

    def test_index_page(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)

    def test_about_page(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)

    def test_buy_page(self):
        response = self.client.get(reverse('buy'))
        self.assertEqual(response.status_code, 200)

    def test_search_page(self):
        response = self.client.get(reverse('search'), {'q': 'test'})
        self.assertEqual(response.status_code, 200)

    def test_product_detail(self):
        response = self.client.get(reverse('product_detail', args=['cloth', self.cloth.id]))
        self.assertEqual(response.status_code, 200)

    def test_login_page(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_signup_page(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)

    def test_login_and_redirect(self):
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'TestPass123!'})
        self.assertEqual(response.status_code, 302)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)

    def test_cart_page(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)

    def test_add_to_cart(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.post(
            reverse('add_to_cart', args=['toy', self.toy.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

    def test_wishlist_add(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(reverse('add_to_wishlist', args=['cloth', self.cloth.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(WishlistItem.objects.filter(user=self.user).count(), 1)

    def test_checkout_empty_cart(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 302)

    def test_stock_status_api(self):
        Inventory.objects.create(product_type='toy', toy=self.toy, stock=10)
        response = self.client.get(reverse('stock_status_api'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('products', data)

    def test_api_products(self):
        response = self.client.get(reverse('api_products'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('products', data)

    def test_validate_coupon(self):
        Coupon.objects.create(
            code='TESTCPN', discount_type='percentage', discount_value=Decimal('10'),
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=30),
            is_active=True,
        )
        response = self.client.post(
            reverse('validate_coupon'),
            data='{"code": "TESTCPN", "subtotal": 1000}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['valid'])

    def test_validate_coupon_invalid(self):
        response = self.client.post(
            reverse('validate_coupon'),
            data='{"code": "NONEXISTENT", "subtotal": 1000}',
            content_type='application/json',
        )
        data = response.json()
        self.assertFalse(data['valid'])

    def test_shop_offers_page(self):
        response = self.client.get(reverse('shop_offers'))
        self.assertEqual(response.status_code, 200)

    def test_new_arrivals_page(self):
        response = self.client.get(reverse('new_arrivals'))
        self.assertEqual(response.status_code, 200)

    def test_kids_cloths_page(self):
        response = self.client.get(reverse('kids_cloths'))
        self.assertEqual(response.status_code, 200)

    def test_women_cloths_page(self):
        response = self.client.get(reverse('women_cloths'))
        self.assertEqual(response.status_code, 200)

    def test_mens_cloths_page(self):
        response = self.client.get(reverse('mens_cloths'))
        self.assertEqual(response.status_code, 200)

    def test_toys_page(self):
        response = self.client.get(reverse('toys_page'))
        self.assertEqual(response.status_code, 200)

    def test_cloths_page(self):
        response = self.client.get(reverse('cloths'))
        self.assertEqual(response.status_code, 200)

    def test_reviews_page(self):
        response = self.client.get(reverse('reviews'))
        self.assertEqual(response.status_code, 200)

    def test_contact_page(self):
        response = self.client.get(reverse('contact_us'))
        self.assertEqual(response.status_code, 200)

    def test_search_empty_query(self):
        response = self.client.get(reverse('search'), {'q': ''})
        self.assertEqual(response.status_code, 200)

    def test_product_detail_toy(self):
        response = self.client.get(reverse('product_detail', args=['toy', self.toy.id]))
        self.assertEqual(response.status_code, 200)

    def test_product_detail_invalid_type(self):
        response = self.client.get(reverse('product_detail', args=['invalid', 1]))
        self.assertEqual(response.status_code, 302)

    def test_cart_details_page(self):
        response = self.client.get(reverse('cart_details'))
        self.assertEqual(response.status_code, 200)

    def test_get_cart_data_api(self):
        response = self.client.get(reverse('get_cart_data'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['cart_count'], 0)

    def test_add_to_cart_invalid_type(self):
        response = self.client.post(
            reverse('add_to_cart', args=['invalid', 1]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 400)

    def test_wishlist_requires_login(self):
        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 302)

    def test_checkout_requires_login(self):
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 302)

    def test_my_orders_requires_login(self):
        response = self.client.get(reverse('my_orders'))
        self.assertEqual(response.status_code, 302)

    def test_payment_page_requires_login(self):
        response = self.client.get(reverse('payment_page'))
        self.assertEqual(response.status_code, 302)

    def test_profile_authenticated(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_my_orders_authenticated(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(reverse('my_orders'))
        self.assertEqual(response.status_code, 200)

    def test_wishlist_authenticated(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 200)

    def test_update_cart_item(self):
        self.client.login(username='testuser', password='TestPass123!')
        cart = Cart.objects.create(user=self.user)
        ci = CartItem.objects.create(cart=cart, item_type='toy', toy=self.toy, quantity=1)
        response = self.client.post(
            reverse('update_cart_item', args=[ci.id]),
            data='{"quantity": 3}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        ci.refresh_from_db()
        self.assertEqual(ci.quantity, 3)

    def test_remove_from_cart(self):
        self.client.login(username='testuser', password='TestPass123!')
        cart = Cart.objects.create(user=self.user)
        ci = CartItem.objects.create(cart=cart, item_type='toy', toy=self.toy, quantity=1)
        response = self.client.post(reverse('remove_from_cart', args=[ci.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CartItem.objects.filter(id=ci.id).exists())

    def test_clear_cart(self):
        self.client.login(username='testuser', password='TestPass123!')
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, item_type='toy', toy=self.toy, quantity=1)
        response = self.client.post(reverse('clear_cart'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(cart.items.count(), 0)

    def test_signup_flow(self):
        response = self.client.post(reverse('signup'), {
            'username': 'newuser', 'email': 'new@test.com',
            'password': 'StrongPass123!', 'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_signup_password_mismatch(self):
        response = self.client.post(reverse('signup'), {
            'username': 'newuser2', 'email': 'new2@test.com',
            'password': 'StrongPass123!', 'password2': 'DifferentPass123!',
        })
        self.assertEqual(response.status_code, 200)  # stays on signup page

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'wrongpass'})
        self.assertEqual(response.status_code, 200)  # stays on login page

    def test_logout(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)

    def test_update_profile(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.post(
            reverse('update_profile'),
            data='{"first_name": "Test", "last_name": "User"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Test')

    def test_change_password(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.post(
            reverse('change_password'),
            data='{"current_password": "TestPass123!", "new_password": "NewStrongPass456!", "confirm_password": "NewStrongPass456!"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStrongPass456!'))

    def test_change_password_wrong_current(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.post(
            reverse('change_password'),
            data='{"current_password": "wrong", "new_password": "New123!", "confirm_password": "New123!"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_product_variants_api(self):
        response = self.client.get(reverse('get_product_variants', args=[self.cloth.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('variants', data)

    def test_dashboard_requires_staff(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)  # redirect to login

    def test_dashboard_staff_access(self):
        self.user.is_staff = True
        self.user.save()
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_api_products_with_filter(self):
        response = self.client.get(reverse('api_products'), {'type': 'cloth', 'q': 'test'})
        self.assertEqual(response.status_code, 200)

    def test_search_ajax(self):
        response = self.client.get(
            reverse('search'), {'q': 'test'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)

    def test_checkout_full_flow(self):
        self.client.login(username='testuser', password='TestPass123!')
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, item_type='toy', toy=self.toy, quantity=1)
        response = self.client.post(reverse('checkout'), {
            'full_name': 'Test User', 'email': 'test@test.com', 'phone': '123456',
            'address': '123 Main St', 'city': 'Colombo', 'postal_code': '10100',
            'country': 'LK', 'payment_method': 'cash_on_delivery',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Order.objects.filter(user=self.user).exists())

    def test_order_success_page(self):
        self.client.login(username='testuser', password='TestPass123!')
        order = Order.objects.create(
            user=self.user, order_number='ORD-VIEW0001',
            full_name='Test', email='t@t.com', phone='1', address='a',
            city='c', postal_code='p', country='c',
            subtotal=Decimal('100'), tax=Decimal('10'), total=Decimal('110'),
        )
        response = self.client.get(reverse('order_success', args=[order.order_number]))
        self.assertEqual(response.status_code, 200)

    def test_order_tracking_page(self):
        self.client.login(username='testuser', password='TestPass123!')
        order = Order.objects.create(
            user=self.user, order_number='ORD-TRACK001',
            full_name='Test', email='t@t.com', phone='1', address='a',
            city='c', postal_code='p', country='c',
            subtotal=Decimal('100'), tax=Decimal('10'), total=Decimal('110'),
        )
        response = self.client.get(reverse('order_tracking', args=[order.order_number]))
        self.assertEqual(response.status_code, 200)

    def test_reorder(self):
        self.client.login(username='testuser', password='TestPass123!')
        order = Order.objects.create(
            user=self.user, order_number='ORD-REORDER1',
            full_name='Test', email='t@t.com', phone='1', address='a',
            city='c', postal_code='p', country='c',
            subtotal=Decimal('750'), tax=Decimal('75'), total=Decimal('825'),
        )
        OrderItem.objects.create(
            order=order, item_name='View Test Toy', item_type='toy',
            quantity=1, price=Decimal('750'), subtotal=Decimal('750'),
        )
        response = self.client.get(reverse('reorder', args=[order.order_number]))
        self.assertEqual(response.status_code, 302)


class ContextProcessorTests(TestCase):
    def test_breadcrumbs_on_about(self):
        response = self.client.get(reverse('about'))
        self.assertIn('breadcrumbs', response.context)
        crumbs = response.context['breadcrumbs']
        self.assertEqual(len(crumbs), 1)
        self.assertEqual(crumbs[0]['label'], 'About Us')

    def test_breadcrumbs_on_home(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.context['breadcrumbs'], [])

    def test_cart_count_in_context(self):
        response = self.client.get(reverse('index'))
        self.assertIn('cart_count', response.context)
        self.assertEqual(response.context['cart_count'], 0)

    def test_admin_dashboard_requires_staff(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)

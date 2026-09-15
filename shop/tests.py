from decimal import Decimal
from django.test import TestCase
from accounts.models import User
from books.models import Author, Book
from .models import CartItem, Entitlement, Order, WalletTransaction

class ShopFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='pass123')
        self.author = Author.objects.create(name='Test Author')
        self.book = Book.objects.create(
            name='Test Book', slug='shop-test-book', author=self.author,
            price=100000, status='published', visibility='public'
        )
        self.client.login(username='buyer', password='pass123')

    def test_wallet_page_requires_login(self):
        self.client.logout()
        response = self.client.get('/shop/wallet/')
        self.assertEqual(response.status_code, 302)

    def test_checkout_deducts_wallet_and_creates_entitlement(self):
        self.user.wallet_balance = Decimal('200000')
        self.user.save(update_fields=['wallet_balance'])
        CartItem.objects.create(user=self.user, book=self.book)
        response = self.client.post('/shop/checkout/', {})
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.wallet_balance, Decimal('90000'))
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.total, Decimal('110000'))
        self.assertTrue(Entitlement.objects.filter(user=self.user, book=self.book).exists())
        self.assertTrue(WalletTransaction.objects.filter(user=self.user, type='debit', order=order).exists())
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())

    def test_checkout_rejects_insufficient_balance(self):
        self.user.wallet_balance = Decimal('100000')
        self.user.save(update_fields=['wallet_balance'])
        CartItem.objects.create(user=self.user, book=self.book)
        response = self.client.post('/shop/checkout/', {})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.wallet_balance, Decimal('100000'))
        self.assertFalse(Order.objects.filter(user=self.user).exists())

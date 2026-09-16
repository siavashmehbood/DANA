from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from books.models import Author, Book
from .models import CartItem, CheckoutRequest, Coupon, Entitlement, Order, Payment, Referral, WalletTransaction

class ShopFlowTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='buyer',password='pass12345')
        self.author=Author.objects.create(name='Test Author')
        self.book=Book.objects.create(name='Test Book',slug='shop-test-book',author=self.author,price=100000,status='published',visibility='public')
        self.client.login(username='buyer',password='pass12345')

    def _checkout(self,key='checkout-test-key'):
        CartItem.objects.get_or_create(user=self.user,book=self.book)
        return self.client.post(reverse('checkout'),{'action':'pay','idempotency_key':key})

    def test_wallet_page_requires_login(self):
        self.client.logout(); self.assertEqual(self.client.get('/shop/wallet/').status_code,302)

    def test_checkout_deducts_wallet_and_creates_entitlement(self):
        self.user.wallet_balance=Decimal('200000'); self.user.save(update_fields=['wallet_balance']); response=self._checkout()
        self.assertEqual(response.status_code,200); self.user.refresh_from_db(); self.assertEqual(self.user.wallet_balance,Decimal('90000'))
        order=Order.objects.get(user=self.user); self.assertEqual(order.total,Decimal('110000')); self.assertTrue(Entitlement.objects.filter(user=self.user,book=self.book).exists())
        tx=WalletTransaction.objects.get(user=self.user,type='debit',order=order); self.assertEqual(tx.balance_before,Decimal('200000')); self.assertEqual(tx.balance_after,Decimal('90000')); self.assertTrue(Payment.objects.filter(order=order,status='successful').exists())

    def test_checkout_is_idempotent(self):
        self.user.wallet_balance=Decimal('200000'); self.user.save(update_fields=['wallet_balance']); self._checkout('same-key'); self._checkout('same-key')
        self.assertEqual(Order.objects.filter(user=self.user).count(),1); self.assertEqual(WalletTransaction.objects.filter(user=self.user,type='debit').count(),1); self.assertEqual(CheckoutRequest.objects.filter(user=self.user,idempotency_key='same-key').count(),1)

    def test_checkout_rejects_insufficient_balance(self):
        self.user.wallet_balance=Decimal('100000'); self.user.save(update_fields=['wallet_balance']); response=self._checkout(); self.assertEqual(response.status_code,302); self.user.refresh_from_db(); self.assertEqual(self.user.wallet_balance,Decimal('100000')); self.assertFalse(Order.objects.filter(user=self.user).exists())

    def test_coupon_is_applied_only_when_requested(self):
        self.user.wallet_balance=Decimal('200000'); self.user.save(update_fields=['wallet_balance']); Coupon.objects.create(code='DANA10',percent=10,capacity=1); CartItem.objects.create(user=self.user,book=self.book)
        response=self.client.post(reverse('checkout'),{'action':'apply_coupon','coupon':'DANA10','idempotency_key':'coupon-key'}); self.assertEqual(response.status_code,302); response=self._checkout('coupon-key'); self.assertEqual(response.status_code,200)
        order=Order.objects.get(user=self.user); self.assertEqual(order.discount,Decimal('10000')); self.assertEqual(Coupon.objects.get(code='DANA10').used,1)

    def test_referral_reward_is_only_granted_once(self):
        inviter=User.objects.create_user(username='inviter',password='pass12345'); Referral.objects.create(inviter=inviter,invitee=self.user); self.user.wallet_balance=Decimal('200000'); self.user.save(update_fields=['wallet_balance']); self._checkout('ref-key')
        inviter.refresh_from_db(); self.user.refresh_from_db(); self.assertEqual(inviter.wallet_balance,Decimal('50000')); self.assertEqual(self.user.wallet_balance,Decimal('140000')); self.assertEqual(WalletTransaction.objects.filter(type='reward').count(),2)

from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
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

    @override_settings(ZARINPAL_MERCHANT_ID='test-merchant')
    @patch('shop.payment.requests.post')
    def test_bank_payment_request_creates_pending_payment(self, post):
        response_data=Mock(); response_data.raise_for_status.return_value=None; response_data.json.return_value={'data':{'code':100,'authority':'A123'}}
        post.return_value=response_data
        CartItem.objects.create(user=self.user,book=self.book)
        response=self.client.post(reverse('bank_checkout'))
        self.assertEqual(response.status_code,302)
        self.assertEqual(response['Location'],'https://payment.zarinpal.com/pg/StartPay/A123')
        payment=Payment.objects.get(order__user=self.user,provider='zarinpal')
        self.assertEqual(payment.status,'pending'); self.assertEqual(payment.authority,'A123')
        self.assertEqual(Order.objects.get(pk=payment.order_id).status,'pending')

    @override_settings(ZARINPAL_MERCHANT_ID='test-merchant')
    @patch('shop.payment.requests.post')
    def test_bank_callback_verifies_and_grants_entitlement(self, post):
        request_response=Mock(); request_response.raise_for_status.return_value=None; request_response.json.return_value={'data':{'code':100,'authority':'A456'}}
        verify_response=Mock(); verify_response.raise_for_status.return_value=None; verify_response.json.return_value={'data':{'code':100,'ref_id':'999'}}
        post.side_effect=[request_response,verify_response]
        CartItem.objects.create(user=self.user,book=self.book)
        start=self.client.post(reverse('bank_checkout'))
        self.assertEqual(start.status_code,302)
        callback=self.client.get(reverse('payment_callback'),{'Authority':'A456','Status':'OK'})
        self.assertEqual(callback.status_code,200)
        order=Order.objects.get(user=self.user); payment=Payment.objects.get(order=order)
        self.assertEqual(order.status,'paid'); self.assertEqual(payment.status,'successful'); self.assertTrue(Entitlement.objects.filter(user=self.user,book=self.book).exists())
        self.assertFalse(CartItem.objects.filter(user=self.user,book=self.book).exists())

    @override_settings(ZARINPAL_MERCHANT_ID='')
    def test_bank_payment_is_blocked_without_merchant_configuration(self):
        CartItem.objects.create(user=self.user,book=self.book)
        response=self.client.post(reverse('bank_checkout'))
        self.assertEqual(response.status_code,302)
        self.assertEqual(response.url,reverse('checkout'))
        self.assertFalse(Payment.objects.filter(provider='zarinpal').exists())

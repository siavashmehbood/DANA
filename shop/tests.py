from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from books.models import Author, Book
from .models import CartItem, CheckoutRequest, Coupon, Entitlement, Order, Payment, Referral, WalletTransaction, SubscriptionPlan, Subscription


class ShopFlowTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='buyer',password='pass12345')
        self.author=Author.objects.create(name='Test Author')
        self.book=Book.objects.create(name='Test Book',slug='shop-test-book',author=self.author,price=100000,status='published',visibility='public')
        self.client.login(username='buyer',password='pass12345')

    def _checkout(self,key='checkout-test-key'):
        CartItem.objects.get_or_create(user=self.user,book=self.book)
        return self.client.post(reverse('checkout'),{'action':'pay','idempotency_key':key})

    def _subscribe(self, plan):
        self.client.get(reverse('subscriptions'))
        key=self.client.session['subscription_activation_key']
        return self.client.post(reverse('subscribe',args=[plan.slug]),{'activation_key':key})

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
        self.assertEqual(order.status,'paid'); self.assertEqual(payment.status,'successful'); self.assertEqual(payment.reference_id,'999'); self.assertTrue(Entitlement.objects.filter(user=self.user,book=self.book).exists())
        self.assertFalse(CartItem.objects.filter(user=self.user,book=self.book).exists())

    @override_settings(ZARINPAL_MERCHANT_ID='')
    def test_bank_payment_is_blocked_without_merchant_configuration(self):
        CartItem.objects.create(user=self.user,book=self.book)
        response=self.client.post(reverse('bank_checkout'))
        self.assertEqual(response.status_code,302)
        self.assertEqual(response.url,reverse('checkout'))
        self.assertFalse(Payment.objects.filter(provider='zarinpal').exists())


    def test_expired_entitlement_does_not_block_repurchase(self):
        self.user.wallet_balance=Decimal('200000'); self.user.save(update_fields=['wallet_balance'])
        Entitlement.objects.create(user=self.user,book=self.book,expires_at=timezone.now()-timedelta(minutes=1),source='subscription')
        CartItem.objects.create(user=self.user,book=self.book)
        response=self.client.post(reverse('checkout'),{'action':'pay','idempotency_key':'repurchase-key'})
        self.assertEqual(response.status_code,200)
        self.assertTrue(Order.objects.filter(user=self.user,status='paid').exists())

    @override_settings(ZARINPAL_MERCHANT_ID='test-merchant')
    @patch('shop.payment.requests.post')
    def test_cancelled_callback_cannot_later_verify_same_payment(self, post):
        request_response=Mock(); request_response.raise_for_status.return_value=None; request_response.json.return_value={'data':{'code':100,'authority':'A789'}}
        post.return_value=request_response
        CartItem.objects.create(user=self.user,book=self.book)
        self.client.post(reverse('bank_checkout'))
        first=self.client.get(reverse('payment_callback'),{'Authority':'A789','Status':'NOK'})
        self.assertEqual(first.status_code,302)
        second=self.client.get(reverse('payment_callback'),{'Authority':'A789','Status':'OK'})
        self.assertEqual(second.status_code,302)
        payment=Payment.objects.get(authority='A789')
        self.assertEqual(payment.status,'cancelled')
        self.assertFalse(Entitlement.objects.filter(user=self.user,book=self.book).exists())
        self.assertEqual(post.call_count,1)


    def test_unpublished_book_cannot_be_purchased(self):
        draft=Book.objects.create(name='Draft sale',slug='draft-sale',author=self.author,price=1000,status='draft')
        response=self.client.post(reverse('cart'),{'book_id':draft.pk})
        self.assertEqual(response.status_code,302)
        self.assertFalse(CartItem.objects.filter(user=self.user,book=draft).exists())


    def test_cart_removes_book_that_becomes_unpublished(self):
        item=CartItem.objects.create(user=self.user,book=self.book)
        self.book.status='draft'; self.book.save(update_fields=['status'])
        response=self.client.get(reverse('cart'))
        self.assertEqual(response.status_code,200)
        self.assertFalse(CartItem.objects.filter(pk=item.pk).exists())


    def test_order_history_is_user_scoped(self):
        other=User.objects.create_user(username='other-orders',password='pass12345')
        mine=Order.objects.create(user=self.user,subtotal=100,discount=0,tax=0,total=100,status='paid',tracking_code='MINE-1')
        Order.objects.create(user=other,subtotal=100,discount=0,tax=0,total=100,status='paid',tracking_code='OTHER-1')
        response=self.client.get(reverse('orders'))
        self.assertContains(response,'MINE-1')
        self.assertNotContains(response,'OTHER-1')


    def test_subscription_catalog_shows_active_plans(self):
        SubscriptionPlan.objects.create(name='ماهانه',slug='monthly',price=100000,duration_days=30,active=True)
        SubscriptionPlan.objects.create(name='خاموش',slug='inactive',price=1,duration_days=1,active=False)
        response=self.client.get(reverse('subscriptions'))
        self.assertContains(response,'ماهانه')
        self.assertNotContains(response,'خاموش')


    def test_subscription_active_state_obeys_period(self):
        plan=SubscriptionPlan.objects.create(name='Active plan',slug='active-plan',price=10,duration_days=30)
        sub=Subscription.objects.create(user=self.user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=1))
        self.assertTrue(sub.is_active)
        sub.status='cancelled'
        self.assertFalse(sub.is_active)


    def test_future_subscription_is_not_shown_as_active(self):
        plan=SubscriptionPlan.objects.create(name='Future',slug='future-plan',price=10,duration_days=30)
        Subscription.objects.create(user=self.user,plan=plan,starts_at=timezone.now()+timedelta(days=1),expires_at=timezone.now()+timedelta(days=31))
        response=self.client.get(reverse('subscriptions'))
        self.assertNotContains(response,'اشتراک فعال: Future')


    def test_featured_subscription_is_listed_first(self):
        SubscriptionPlan.objects.create(name='Regular',slug='regular-plan',price=1,duration_days=30)
        SubscriptionPlan.objects.create(name='Featured',slug='featured-plan',price=999,duration_days=30,featured=True)
        response=self.client.get(reverse('subscriptions'))
        self.assertLess(response.content.decode().find('Featured'),response.content.decode().find('Regular'))


    def test_subscription_period_constraint_rejects_invalid_range(self):
        from django.db import IntegrityError
        plan=SubscriptionPlan.objects.create(name='Range',slug='range-plan',price=10,duration_days=30)
        with self.assertRaises(IntegrityError):
            Subscription.objects.create(user=self.user,plan=plan,starts_at=timezone.now(),expires_at=timezone.now()-timedelta(days=1))


    def test_free_subscription_can_be_activated(self):
        plan=SubscriptionPlan.objects.create(name='Free Catalog',slug='free-catalog',price=0,duration_days=7,grants_catalog_access=True)
        self.client.login(username='buyer',password='pass12345')
        response=self._subscribe(plan)
        self.assertRedirects(response,reverse('subscriptions'))
        self.assertTrue(Subscription.objects.filter(user=self.user,plan=plan,status='active').exists())

    def test_paid_subscription_requires_sufficient_wallet_balance(self):
        plan=SubscriptionPlan.objects.create(name='Paid Catalog',slug='paid-catalog',price=100,duration_days=30)
        self._subscribe(plan)
        self.assertFalse(Subscription.objects.filter(user=self.user,plan=plan).exists())

    def test_paid_subscription_debits_wallet_and_activates(self):
        plan=SubscriptionPlan.objects.create(name='Wallet Plus',slug='wallet-plus',price=100,duration_days=30)
        self.user.wallet_balance=Decimal('250')
        self.user.save(update_fields=['wallet_balance'])
        response=self._subscribe(plan)
        self.assertRedirects(response,reverse('subscriptions'))
        self.user.refresh_from_db()
        sub=Subscription.objects.get(user=self.user,plan=plan,status='active')
        self.assertEqual(self.user.wallet_balance,Decimal('150'))
        tx=WalletTransaction.objects.get(reference=f'subscription:{sub.pk}:debit')
        self.assertEqual(tx.balance_before,Decimal('250'))
        self.assertEqual(tx.balance_after,Decimal('150'))


    def test_reactivating_same_free_plan_extends_from_current_expiry(self):
        plan=SubscriptionPlan.objects.create(name='Free Extend',slug='free-extend',price=0,duration_days=7)
        current=Subscription.objects.create(user=self.user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=2))
        self.client.login(username='buyer',password='pass12345')
        self._subscribe(plan)
        newest=Subscription.objects.filter(user=self.user,plan=plan).order_by('-created_at').first()
        self.assertGreaterEqual(newest.starts_at,current.expires_at)


    def test_reactivating_same_free_plan_leaves_one_active_row(self):
        plan=SubscriptionPlan.objects.create(name='Single Active',slug='single-active',price=0,duration_days=7)
        Subscription.objects.create(user=self.user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=2))
        self.client.login(username='buyer',password='pass12345')
        self._subscribe(plan)
        self.assertEqual(Subscription.objects.filter(user=self.user,plan=plan,status='active').count(),1)


    def test_subscription_page_marks_elapsed_active_rows_expired(self):
        plan=SubscriptionPlan.objects.create(name='Elapsed',slug='elapsed',price=0,duration_days=1)
        sub=Subscription.objects.create(user=self.user,plan=plan,status='active',starts_at=timezone.now()-timedelta(days=2),expires_at=timezone.now()-timedelta(days=1))
        self.client.login(username='buyer',password='pass12345')
        self.client.get(reverse('subscriptions'))
        sub.refresh_from_db()
        self.assertEqual(sub.status,'expired')


    def test_retired_plan_remains_visible_for_existing_subscription(self):
        plan=SubscriptionPlan.objects.create(name='Disabled Current',slug='disabled-current',price=0,duration_days=7,active=False)
        Subscription.objects.create(user=self.user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=2))
        self.client.login(username='buyer',password='pass12345')
        response=self.client.get(reverse('subscriptions'))
        self.assertIsNotNone(response.context['current_subscription'])
        self.assertEqual(response.context['current_subscription'].plan_id,plan.id)


    def test_free_plan_cannot_queue_duplicate_future_renewals(self):
        plan=SubscriptionPlan.objects.create(name='Queue Safe',slug='queue-safe',price=0,duration_days=7)
        Subscription.objects.create(user=self.user,plan=plan,starts_at=timezone.now()+timedelta(days=2),expires_at=timezone.now()+timedelta(days=9))
        self.client.login(username='buyer',password='pass12345')
        self._subscribe(plan)
        self.assertEqual(Subscription.objects.filter(user=self.user,plan=plan).count(),1)


    def test_switching_free_plan_preserves_previous_active_membership(self):
        old=SubscriptionPlan.objects.create(name='Old Free',slug='old-free',price=0,duration_days=7)
        new=SubscriptionPlan.objects.create(name='New Free',slug='new-free',price=0,duration_days=7)
        previous=Subscription.objects.create(user=self.user,plan=old,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=2))
        self.client.login(username='buyer',password='pass12345')
        self._subscribe(new)
        previous.refresh_from_db()
        self.assertEqual(previous.status,'active')
        self.assertFalse(Subscription.objects.filter(user=self.user,plan=new).exists())
        self.assertEqual(Subscription.objects.filter(user=self.user,status='active').count(),1)


    def test_database_rejects_two_active_subscriptions_for_same_user(self):
        from django.db import IntegrityError
        first=SubscriptionPlan.objects.create(name='Constraint A',slug='constraint-a',price=0,duration_days=7)
        second=SubscriptionPlan.objects.create(name='Constraint B',slug='constraint-b',price=0,duration_days=7)
        Subscription.objects.create(user=self.user,plan=first,starts_at=timezone.now(),expires_at=timezone.now()+timedelta(days=7))
        with self.assertRaises(IntegrityError):
            Subscription.objects.create(user=self.user,plan=second,starts_at=timezone.now(),expires_at=timezone.now()+timedelta(days=7))


    @override_settings(ZARINPAL_MERCHANT_ID='test-merchant')
    @patch('shop.payment.requests.post')
    def test_bank_checkout_does_not_repurchase_owned_book(self, post):
        Entitlement.objects.create(user=self.user,book=self.book,source='purchase')
        CartItem.objects.create(user=self.user,book=self.book)
        response=self.client.post(reverse('bank_checkout'))
        self.assertEqual(response.status_code,302)
        self.assertEqual(response.url,reverse('cart'))
        self.assertFalse(Order.objects.filter(user=self.user).exists())
        post.assert_not_called()


    def test_subscription_activation_token_blocks_duplicate_post(self):
        plan=SubscriptionPlan.objects.create(name='Idempotent Plus',slug='idempotent-plus',price=100,duration_days=30)
        self.user.wallet_balance=Decimal('500')
        self.user.save(update_fields=['wallet_balance'])
        self.client.get(reverse('subscriptions'))
        key=self.client.session['subscription_activation_key']
        url=reverse('subscribe',args=[plan.slug])
        first=self.client.post(url,{'activation_key':key})
        second=self.client.post(url,{'activation_key':key})
        self.user.refresh_from_db()
        self.assertEqual(first.status_code,302)
        self.assertEqual(second.status_code,302)
        self.assertEqual(self.user.wallet_balance,Decimal('400'))
        self.assertEqual(WalletTransaction.objects.filter(user=self.user,reason='Subscription purchase').count(),1)


    def test_queued_subscription_blocks_overlapping_second_plan(self):
        first=SubscriptionPlan.objects.create(name='First queued',slug='first-queued',price=0,duration_days=30)
        second=SubscriptionPlan.objects.create(name='Second queued',slug='second-queued',price=0,duration_days=30)
        now=timezone.now()
        Subscription.objects.create(user=self.user,plan=first,status='active',starts_at=now+timedelta(days=1),expires_at=now+timedelta(days=31))
        response=self._subscribe(second)
        self.assertEqual(response.status_code,302)
        self.assertFalse(Subscription.objects.filter(user=self.user,plan=second).exists())


    def test_retired_plan_does_not_revoke_existing_subscription(self):
        plan=SubscriptionPlan.objects.create(name='Disabled active state',slug='disabled-active-state',price=0,duration_days=30,active=False)
        sub=Subscription.objects.create(user=self.user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=1))
        self.assertTrue(sub.is_active)


    def test_bank_callback_cannot_use_another_users_authority(self):
        other=User.objects.create_user(username='other-bank-user',password='pass12345')
        order=Order.objects.create(user=other,subtotal=100,discount=0,tax=0,total=100,status='pending',tracking_code='998877')
        Payment.objects.create(user=other,order=order,provider='zarinpal',amount=100,status='pending',authority='private-authority',idempotency_key='private-payment')
        self.client.force_login(self.user)
        response=self.client.get(reverse('payment_callback'),{'Authority':'private-authority','Status':'OK'})
        self.assertEqual(response.status_code,302)
        order.refresh_from_db()
        self.assertEqual(order.status,'pending')


    @override_settings(ZARINPAL_MERCHANT_ID='test-merchant')
    @patch('shop.payment.requests.post')
    def test_cancelled_bank_payment_releases_coupon_reservation(self, post):
        response_data=Mock(); response_data.raise_for_status.return_value=None; response_data.json.return_value={'data':{'code':100,'authority':'COUPON-AUTH'}}
        post.return_value=response_data
        coupon=Coupon.objects.create(code='BANK10',percent=10,capacity=1)
        CartItem.objects.create(user=self.user,book=self.book)
        session=self.client.session; session['checkout_coupon']='BANK10'; session.save()
        self.client.post(reverse('bank_checkout'))
        coupon.refresh_from_db(); self.assertEqual(coupon.used,1)
        self.client.get(reverse('payment_callback'),{'Authority':'COUPON-AUTH','Status':'NOK'})
        coupon.refresh_from_db(); self.assertEqual(coupon.used,0)


    def test_subscription_renewal_ignores_future_row_when_no_current_membership(self):
        plan=SubscriptionPlan.objects.create(name='Future Guard',slug='future-guard',price=0,duration_days=7)
        future=Subscription.objects.create(user=self.user,plan=plan,status='cancelled',starts_at=timezone.now()+timedelta(days=3),expires_at=timezone.now()+timedelta(days=10))
        response=self._subscribe(plan)
        self.assertEqual(response.status_code,302)
        active=Subscription.objects.get(user=self.user,status='active')
        self.assertLessEqual(active.starts_at,timezone.now())
        future.refresh_from_db()
        self.assertEqual(future.status,'cancelled')


    def test_activation_expires_stale_active_membership_before_new_plan(self):
        old=SubscriptionPlan.objects.create(name='Stale',slug='stale-plan',price=0,duration_days=7)
        new=SubscriptionPlan.objects.create(name='Fresh',slug='fresh-plan',price=0,duration_days=7)
        stale=Subscription.objects.create(user=self.user,plan=old,status='active',starts_at=timezone.now()-timedelta(days=9),expires_at=timezone.now()-timedelta(days=2))
        response=self._subscribe(new)
        self.assertEqual(response.status_code,302)
        stale.refresh_from_db()
        self.assertEqual(stale.status,'expired')
        self.assertTrue(Subscription.objects.filter(user=self.user,plan=new,status='active').exists())


    def test_switching_plan_does_not_destroy_remaining_paid_membership(self):
        old=SubscriptionPlan.objects.create(name='Paid Current',slug='paid-current',price=100,duration_days=30)
        new=SubscriptionPlan.objects.create(name='Other Plan',slug='other-plan',price=50,duration_days=30)
        current=Subscription.objects.create(user=self.user,plan=old,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=20))
        self.user.wallet_balance=Decimal('500')
        self.user.save(update_fields=['wallet_balance'])
        response=self._subscribe(new)
        self.assertEqual(response.status_code,302)
        current.refresh_from_db(); self.user.refresh_from_db()
        self.assertEqual(current.status,'active')
        self.assertFalse(Subscription.objects.filter(user=self.user,plan=new).exists())
        self.assertEqual(self.user.wallet_balance,Decimal('500'))


    def test_subscription_catalog_refresh_changes_activation_nonce(self):
        self.client.get(reverse('subscriptions'))
        first=self.client.session['subscription_activation_key']
        self.client.get(reverse('subscriptions'))
        second=self.client.session['subscription_activation_key']
        self.assertNotEqual(first,second)


    def test_subscription_catalog_disables_switch_while_membership_active(self):
        current_plan=SubscriptionPlan.objects.create(name='Current UI',slug='current-ui',price=0,duration_days=7)
        other_plan=SubscriptionPlan.objects.create(name='Other UI',slug='other-ui',price=0,duration_days=7)
        Subscription.objects.create(user=self.user,plan=current_plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=2))
        self.client.login(username='buyer',password='pass12345')
        response=self.client.get(reverse('subscriptions'))
        self.assertContains(response,'پس از پایان اشتراک فعلی')
        self.assertContains(response,reverse('subscribe',args=[current_plan.slug]))
        self.assertNotContains(response,reverse('subscribe',args=[other_plan.slug]))


    def test_current_subscription_plan_is_marked_in_catalog(self):
        plan=SubscriptionPlan.objects.create(name='Marked Plan',slug='marked-plan',price=0,duration_days=7)
        Subscription.objects.create(user=self.user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=2))
        self.client.login(username='buyer',password='pass12345')
        response=self.client.get(reverse('subscriptions'))
        self.assertContains(response,'پلن فعلی')


    def test_anonymous_subscription_activation_redirects_to_login(self):
        plan=SubscriptionPlan.objects.create(name='Login required',slug='login-required',price=0,duration_days=30)
        self.client.logout()
        response=self.client.post(reverse('subscribe',args=[plan.slug]),{'activation_key':'invalid'})
        self.assertEqual(response.status_code,302)
        self.assertIn('/login/',response.url)
        self.assertFalse(Subscription.objects.filter(plan=plan).exists())


    def test_subscription_catalog_is_private_cache(self):
        response=self.client.get(reverse('subscriptions'))
        self.assertIn('no-store',response.headers.get('Cache-Control',''))
        self.assertEqual(response.headers.get('X-Robots-Tag'),'noindex, nofollow')


    def test_retired_plan_notice_explains_existing_access(self):
        plan=SubscriptionPlan.objects.create(name='Legacy',slug='legacy-plan',price=0,duration_days=7,active=False)
        Subscription.objects.create(user=self.user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=2))
        self.client.login(username='buyer',password='pass12345')
        response=self.client.get(reverse('subscriptions'))
        self.assertContains(response,'اشتراک فعلی شما تا پایان اعتبار فعال است')

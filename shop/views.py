import secrets
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import F
from django.db import models
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache

from accounts.models import User
from books.models import Book
from gamification.models import PointLedger
from gamification.services import add_points, purchase_points_for_amount
from .models import CartItem, CheckoutRequest, Coupon, Entitlement, Order, OrderItem, Payment, Referral, WalletTransaction, SubscriptionPlan, Subscription

REFERRAL_REWARD = Decimal('50000')


def _tracking_code():
    for _ in range(50):
        code = f'{secrets.randbelow(1000000):06d}'
        if not Order.objects.filter(tracking_code=code).exists():
            return code
    raise RuntimeError('Could not generate tracking code')


def _coupon_discount(coupon, subtotal):
    if not coupon or not coupon.active:
        return Decimal(0)
    if coupon.expires_at and coupon.expires_at <= timezone.now():
        return Decimal(0)
    if coupon.used >= coupon.capacity or subtotal < coupon.min_order:
        return Decimal(0)
    raw = subtotal * coupon.percent / 100 if coupon.percent else coupon.amount
    return min(raw, subtotal)


def _wallet_transaction(user, amount, kind, reason, order=None, reference=None):
    amount = Decimal(amount)
    before = user.wallet_balance
    after = before - amount if kind == 'debit' else before + amount
    if after < 0:
        raise ValueError('insufficient_balance')
    user.wallet_balance = after
    user.save(update_fields=['wallet_balance'])
    return WalletTransaction.objects.create(
        user=user, amount=amount, type=kind, reason=reason, order=order,
        balance_before=before, balance_after=after, reference=reference,
    )


def reward_referral(invitee):
    referral = Referral.objects.select_for_update().select_related('inviter').filter(invitee=invitee, rewarded=False).first()
    if not referral:
        return False
    inviter = User.objects.select_for_update().get(pk=referral.inviter_id)
    ref = f'referral:{referral.pk}'
    if WalletTransaction.objects.filter(reference=f'{ref}:inviter').exists():
        referral.rewarded = True
        referral.save(update_fields=['rewarded'])
        return False
    _wallet_transaction(inviter, REFERRAL_REWARD, 'reward', 'Referral reward', reference=f'{ref}:inviter')
    _wallet_transaction(invitee, REFERRAL_REWARD, 'reward', 'Referral reward', reference=f'{ref}:invitee')
    referral.rewarded = True
    referral.save(update_fields=['rewarded'])
    return True


@login_required
def cart(request):
    if request.method == 'POST':
        book = Book.objects.filter(pk=request.POST.get('book_id')).filter(models.Q(status='published')|models.Q(status='scheduled',publish_at__lte=timezone.now())).first()
        if book and not Entitlement.objects.filter(user=request.user, book=book).filter(models.Q(expires_at__isnull=True)|models.Q(expires_at__gt=timezone.now())).exists():
            CartItem.objects.get_or_create(user=request.user, book=book)
        return redirect('cart')
    items = CartItem.objects.filter(user=request.user).select_related('book')
    stale_ids=[i.pk for i in items if not i.book.is_published]
    if stale_ids:
        CartItem.objects.filter(pk__in=stale_ids).delete()
        items = CartItem.objects.filter(user=request.user).select_related('book')
    owned_ids = list(Entitlement.objects.filter(user=request.user, book__in=[i.book for i in items]).filter(models.Q(expires_at__isnull=True)|models.Q(expires_at__gt=timezone.now())).values_list('book_id', flat=True))
    if owned_ids:
        CartItem.objects.filter(user=request.user, book_id__in=owned_ids).delete()
        items = CartItem.objects.filter(user=request.user).select_related('book')
    total = sum((item.book.price for item in items), Decimal(0))
    return render(request, 'shop/cart.html', {'items': items, 'total': total})


@login_required
def remove_cart_item(request, pk):
    if request.method == 'POST':
        CartItem.objects.filter(user=request.user, book_id=pk).delete()
    return redirect('cart')


@login_required
def checkout(request):
    items = [i for i in CartItem.objects.filter(user=request.user).select_related('book') if i.book.is_published]
    items = [i for i in items if not Entitlement.objects.filter(user=request.user, book=i.book).filter(models.Q(expires_at__isnull=True)|models.Q(expires_at__gt=timezone.now())).exists()]
    if not items:
        CartItem.objects.filter(user=request.user).delete()
        return redirect('cart')

    subtotal = sum((item.book.price for item in items), Decimal(0))
    key = request.POST.get('idempotency_key') or request.session.get('checkout_key')
    if not key:
        key = secrets.token_urlsafe(24)
        request.session['checkout_key'] = key

    coupon_code = request.POST.get('coupon', '').strip().upper() or request.session.get('checkout_coupon', '')
    coupon = Coupon.objects.filter(code=coupon_code, active=True).first() if coupon_code else None
    discount = _coupon_discount(coupon, subtotal)
    if coupon_code and discount == 0:
        coupon = None
    tax = ((subtotal - discount) * Decimal('0.10')).quantize(Decimal('1'))
    total = subtotal - discount + tax

    if request.method == 'POST' and request.POST.get('action') == 'apply_coupon':
        if not coupon:
            request.session.pop('checkout_coupon', None)
            messages.error(request, 'کد تخفیف معتبر نیست یا شرایط آن برقرار نیست.')
        else:
            request.session['checkout_coupon'] = coupon.code
            messages.success(request, 'کد تخفیف اعمال شد.')
        return redirect('checkout')

    if request.method == 'POST' and request.POST.get('action') == 'pay':
        if not request.POST.get('idempotency_key'):
            messages.error(request, 'درخواست پرداخت نامعتبر است؛ صفحه را دوباره باز کنید.')
            return redirect('checkout')
        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=request.user.pk)
                request_row, created = CheckoutRequest.objects.get_or_create(user=user, idempotency_key=request.POST['idempotency_key'])
                if not created and request_row.order_id:
                    order = request_row.order
                    return render(request, 'shop/success.html', {'order': order})

                locked_items = list(CartItem.objects.select_for_update().filter(user=user).select_related('book'))
                locked_items = [i for i in locked_items if i.book.is_published]
                owned = set(Entitlement.objects.filter(user=user, book_id__in=[i.book_id for i in locked_items]).filter(models.Q(expires_at__isnull=True)|models.Q(expires_at__gt=timezone.now())).values_list('book_id', flat=True))
                items = [i for i in locked_items if i.book_id not in owned]
                if not items:
                    CartItem.objects.filter(user=user).delete()
                    return redirect('cart')

                subtotal = sum((i.book.price for i in items), Decimal(0))
                locked_coupon = Coupon.objects.select_for_update().filter(code=coupon_code, active=True).first() if coupon_code else None
                discount = _coupon_discount(locked_coupon, subtotal)
                if coupon_code and not locked_coupon:
                    discount = Decimal(0)
                tax = ((subtotal - discount) * Decimal('0.10')).quantize(Decimal('1'))
                total = subtotal - discount + tax
                if user.wallet_balance < total:
                    messages.error(request, 'موجودی کیف پول کافی نیست.')
                    return redirect('checkout')
                if locked_coupon:
                    locked_coupon.used = F('used') + 1
                    locked_coupon.save(update_fields=['used'])

                order = Order.objects.create(user=user, subtotal=subtotal, discount=discount, tax=tax, total=total, status='paid', tracking_code=_tracking_code())
                OrderItem.objects.bulk_create([OrderItem(order=order, book=i.book, price=i.book.price) for i in items])
                for i in items:
                    Entitlement.objects.update_or_create(user=user, book=i.book, defaults={'order':order,'source':'purchase','expires_at':None})
                ref = f'order:{order.pk}:debit'
                _wallet_transaction(user, total, 'debit', 'Book purchase', order=order, reference=ref)
                Payment.objects.create(user=user, order=order, provider='wallet', amount=total, status='successful', idempotency_key=f'payment:{order.pk}')
                add_points(user, PointLedger.PURCHASE, purchase_points_for_amount(total), 'Purchase points', reference=f'order:{order.pk}')
                reward_referral(user)
                CartItem.objects.filter(user=user).delete()
                request_row.order = order
                request_row.save(update_fields=['order'])
                request.session.pop('checkout_key', None)
                request.session.pop('checkout_coupon', None)
            return render(request, 'shop/success.html', {'order': order})
        except IntegrityError:
            messages.error(request, 'درخواست پرداخت تکراری یا نامعتبر بود. وضعیت سفارش را بررسی کنید.')
            return redirect('checkout')

    return render(request, 'shop/checkout.html', {'subtotal': subtotal, 'discount': discount, 'tax': tax, 'total': total, 'checkout_key': key, 'coupon_code': coupon_code})


@login_required
@never_cache
def order_detail(request, tracking_code):
    order = get_object_or_404(Order.objects.prefetch_related('items__book'), tracking_code=tracking_code, user=request.user)
    return render(request, 'shop/order_detail.html', {'order': order})


@login_required
@never_cache
def wallet(request):
    transactions = WalletTransaction.objects.filter(user=request.user).select_related('order').order_by('-created_at')[:50]
    return render(request, 'shop/wallet.html', {'transactions': transactions})


@login_required
@never_cache
def orders(request):
    rows=Order.objects.filter(user=request.user).prefetch_related('items__book').order_by('-created_at')[:100]
    return render(request,'shop/orders.html',{'orders':rows})


@login_required
def subscribe(request, slug):
    if request.method != 'POST':
        return redirect('subscriptions')
    activation_key=request.POST.get('activation_key','')
    if not activation_key or activation_key != request.session.get('subscription_activation_key'):
        messages.error(request,'درخواست فعال‌سازی نامعتبر یا تکراری است؛ صفحه را دوباره باز کنید.')
        return redirect('subscriptions')
    with transaction.atomic():
        user=User.objects.select_for_update().get(pk=request.user.pk)
        plan=get_object_or_404(SubscriptionPlan,slug=slug,active=True)

        now=timezone.now()
        Subscription.objects.select_for_update().filter(user=user,status='active',expires_at__lte=now).update(status='expired')
        if Subscription.objects.select_for_update().filter(user=user,status='active',starts_at__gt=now,expires_at__gt=now).exists():
            messages.info(request,'یک تمدید اشتراک از قبل برای شما ثبت شده است.')
            return redirect('subscriptions')
        active_now=Subscription.objects.select_for_update().filter(user=user,status='active',starts_at__lte=now,expires_at__gt=now).select_related('plan').order_by('-expires_at').first()
        if active_now and active_now.plan_id != plan.id:
            messages.info(request,'برای جلوگیری از از دست رفتن اعتبار، تغییر پلن تا پایان اشتراک فعلی غیرفعال است.')
            return redirect('subscriptions')
        if plan.price > 0 and user.wallet_balance < plan.price:
            messages.error(request,'موجودی کیف پول برای فعال‌سازی این اشتراک کافی نیست.')
            return redirect('subscriptions')
        current=active_now
        if current and current.expires_at <= now:
            current.status='expired'
            current.save(update_fields=['status'])
            current=None
        if current and current.plan_id == plan.id:
            start=current.expires_at
            current.status='expired'
            current.save(update_fields=['status'])
        else:
            if current:
                current.status='cancelled'
                current.save(update_fields=['status'])
            start=now
        subscription=Subscription.objects.create(user=user,plan=plan,starts_at=start,expires_at=start+timezone.timedelta(days=plan.duration_days))
        if plan.price > 0:
            _wallet_transaction(user,plan.price,'debit','Subscription purchase',reference=f'subscription:{subscription.pk}:debit')
            messages.success(request,'اشتراک با موفقیت از کیف پول فعال شد.')
        else:
            messages.success(request,'اشتراک رایگان فعال شد.')
        request.session.pop('subscription_activation_key',None)
    return redirect('subscriptions')


@never_cache
def subscriptions(request):
    if request.method == 'GET':
        request.session['subscription_activation_key']=secrets.token_urlsafe(24)
    plans=SubscriptionPlan.objects.filter(active=True).order_by('-featured','price','duration_days','id')
    current=None
    if request.user.is_authenticated:
        now=timezone.now()
        Subscription.objects.filter(user=request.user,status='active',expires_at__lte=now).update(status='expired')
        current=Subscription.objects.filter(user=request.user,status='active',starts_at__lte=now,expires_at__gt=now).select_related('plan').order_by('-expires_at').first()
    response=render(request,'shop/subscriptions.html',{'plans':plans,'current_subscription':current,'activation_key':request.session['subscription_activation_key']})
    if request.user.is_authenticated:
        response['Cache-Control']='private, no-store'
        response['X-Robots-Tag']='noindex, nofollow'
    return response

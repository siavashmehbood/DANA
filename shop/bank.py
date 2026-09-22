import secrets
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, F
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache

from accounts.models import User
from books.models import Book
from gamification.models import PointLedger
from gamification.services import add_points, purchase_points_for_amount
from .models import CartItem, Coupon, Entitlement, Order, OrderItem, Payment, Referral, WalletTransaction
from .payment import gateway


def _coupon_discount(coupon, subtotal):
    if not coupon or not coupon.active:
        return Decimal(0)
    if coupon.expires_at and coupon.expires_at <= timezone.now():
        return Decimal(0)
    if coupon.used >= coupon.capacity or subtotal < coupon.min_order:
        return Decimal(0)
    raw = subtotal * coupon.percent / 100 if coupon.percent else coupon.amount
    return min(raw, subtotal)


def _release_coupon_reservation(payment):
    payload=payment.callback_payload or {}
    code=payload.get('coupon_code','')
    if not code or not payload.get('coupon_reserved'):
        return
    Coupon.objects.filter(code=code,used__gt=0).update(used=F('used')-1)
    payment.callback_payload={**payload,'coupon_reserved':False}
    payment.save(update_fields=['callback_payload'])


def _tracking_code():
    for _ in range(50):
        code = f'{secrets.randbelow(1000000):06d}'
        if not Order.objects.filter(tracking_code=code).exists():
            return code
    raise RuntimeError('Could not generate tracking code')


@transaction.atomic
def finalize_bank_order(order, payment):
    order = Order.objects.select_for_update().get(pk=order.pk)
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if order.status == 'paid':
        return True
    if payment.status not in ('successful',):
        return False
    items = list(order.items.select_related('book'))
    for item in items:
        Entitlement.objects.get_or_create(user=order.user, book=item.book, defaults={'order': order, 'source': 'purchase'})
    coupon_code = (payment.callback_payload or {}).get('coupon_code', '')
    if coupon_code and not (payment.callback_payload or {}).get('coupon_reserved'):
        Coupon.objects.select_for_update().filter(code=coupon_code, active=True).update(used=F('used') + 1)
    add_points(order.user, PointLedger.PURCHASE, purchase_points_for_amount(order.total), 'Purchase points', reference=f'order:{order.pk}')
    referral = Referral.objects.select_for_update().select_related('inviter').filter(invitee=order.user, rewarded=False).first()
    if referral:
        inviter = User.objects.select_for_update().get(pk=referral.inviter_id)
        for user in (inviter, order.user):
            ref = f'referral:{referral.pk}:{user.pk}'
            if not WalletTransaction.objects.filter(reference=ref).exists():
                before = user.wallet_balance
                user.wallet_balance = before + Decimal('50000')
                user.save(update_fields=['wallet_balance'])
                WalletTransaction.objects.create(user=user, amount=Decimal('50000'), type='reward', reason='Referral reward', balance_before=before, balance_after=user.wallet_balance, reference=ref)
        referral.rewarded = True
        referral.save(update_fields=['rewarded'])
    order.status = 'paid'
    order.save(update_fields=['status'])
    CartItem.objects.filter(user=order.user, book_id__in=[i.book_id for i in items]).delete()
    return True


@login_required
@never_cache
def bank_checkout(request):
    items = [i for i in CartItem.objects.filter(user=request.user).select_related('book') if i.book.is_published]
    owned = set(Entitlement.objects.filter(user=request.user, book_id__in=[i.book_id for i in items]).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).values_list('book_id', flat=True))
    items = [i for i in items if i.book_id not in owned]
    if not items:
        CartItem.objects.filter(user=request.user).delete()
        return redirect('cart')

    subtotal = sum((i.book.price for i in items), Decimal(0))
    coupon_code = request.session.get('checkout_coupon', '')
    coupon = Coupon.objects.filter(code=coupon_code, active=True).first() if coupon_code else None
    discount = _coupon_discount(coupon, subtotal)
    tax = ((subtotal - discount) * Decimal('0.10')).quantize(Decimal('1'))
    total = subtotal - discount + tax

    if request.method == 'POST':
        if not gateway().enabled:
            messages.error(request, 'درگاه بانکی هنوز پیکربندی نشده است.')
            return redirect('checkout')
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            locked_items = list(CartItem.objects.select_for_update().filter(user=user).select_related('book'))
            locked_items = [i for i in locked_items if i.book.is_published]
            owned = set(Entitlement.objects.filter(user=user, book_id__in=[i.book_id for i in locked_items]).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).values_list('book_id', flat=True))
            locked_items = [i for i in locked_items if i.book_id not in owned]
            if not locked_items:
                return redirect('cart')
            subtotal = sum((i.book.price for i in locked_items), Decimal(0))
            coupon = Coupon.objects.select_for_update().filter(code=coupon_code, active=True).first() if coupon_code else None
            discount = _coupon_discount(coupon, subtotal)
            tax = ((subtotal - discount) * Decimal('0.10')).quantize(Decimal('1'))
            total = subtotal - discount + tax
            # Reuse an unfinished bank checkout for the same current cart instead
            # of creating duplicate pending orders when the user double-submits.
            current_book_ids=sorted(i.book_id for i in locked_items)
            reusable=None
            for candidate in Order.objects.filter(user=user,status='pending',payments__provider='zarinpal',payments__status='pending').prefetch_related('items','payments').order_by('-created_at')[:5]:
                if sorted(item.book_id for item in candidate.items.all()) == current_book_ids and candidate.total == total:
                    reusable=candidate
                    break
            if reusable:
                order=reusable
                payment=order.payments.filter(provider='zarinpal',status='pending').order_by('-id').first()
                # A previous gateway request may already have issued an authority;
                # returning to checkout must not reserve a second remote payment.
                if payment and payment.authority:
                    messages.info(request,'یک پرداخت بانکی در انتظار نتیجه دارید؛ وضعیت آن را از سفارش‌های من بررسی کنید.')
                    return redirect('orders')
            else:
                order = Order.objects.create(user=user, subtotal=subtotal, discount=discount, tax=tax, total=total, status='pending', tracking_code=_tracking_code())
                OrderItem.objects.bulk_create([OrderItem(order=order, book=i.book, price=i.book.price) for i in locked_items])
                if coupon and discount > 0:
                    coupon.used=F('used')+1
                    coupon.save(update_fields=['used'])
                payment = Payment.objects.create(user=user, order=order, provider='zarinpal', amount=total, status='pending', idempotency_key=f'bank:{order.pk}', callback_payload={'coupon_code': coupon.code if coupon else '', 'coupon_reserved': bool(coupon and discount > 0)})
            result = gateway().request(order, request)
            if not result.ok:
                payment.status = 'failed'
                payment.callback_payload = {**payment.callback_payload, 'error': result.message}
                payment.save(update_fields=['status', 'callback_payload'])
                _release_coupon_reservation(payment)
                order.status = 'cancelled'
                order.save(update_fields=['status'])
                messages.error(request, result.message)
                return redirect('checkout')
            payment.authority = result.authority
            payment.save(update_fields=['authority'])
        return redirect(result.url)

    return render(request, 'shop/bank_checkout.html', {'subtotal': subtotal, 'discount': discount, 'tax': tax, 'total': total, 'gateway_enabled': gateway().enabled})


@login_required
@never_cache
def payment_callback(request):
    authority = request.GET.get('Authority', '')
    status = request.GET.get('Status', '')
    payment = Payment.objects.select_related('order', 'user').filter(authority=authority, provider='zarinpal', user=request.user).first()
    if not payment:
        messages.error(request, 'تراکنش پیدا نشد.')
        return redirect('cart')
    if payment.status == 'successful':
        return render(request, 'shop/success.html', {'order': payment.order})
    if status != 'OK':
        if payment.status != 'pending':
            messages.error(request, 'وضعیت این تراکنش قبلاً نهایی شده است.')
            return redirect('cart')
        payment.status = 'cancelled'
        payment.callback_payload = {**payment.callback_payload, 'callback_status': status}
        payment.save(update_fields=['status', 'callback_payload'])
        _release_coupon_reservation(payment)
        payment.order.status = 'cancelled'
        payment.order.save(update_fields=['status'])
        messages.warning(request, 'پرداخت توسط کاربر لغو شد.')
        return redirect('checkout')

    if payment.status != 'pending':
        messages.error(request, 'این تراکنش قبلاً نهایی شده است.')
        return redirect('cart')
    result = gateway().verify(payment.order)
    if result.ok:
        with transaction.atomic():
            payment = Payment.objects.select_for_update().select_related('order').get(pk=payment.pk)
            if payment.status == 'successful':
                return render(request, 'shop/success.html', {'order': payment.order})
            if payment.status != 'pending':
                messages.error(request, 'این تراکنش قبلاً نهایی شده است.')
                return redirect('cart')
            payment.status = 'successful'
            payment.reference_id = result.authority
            payment.callback_payload = {**payment.callback_payload, 'ref_id': result.authority}
            payment.save(update_fields=['status', 'reference_id', 'callback_payload'])
            finalize_bank_order(payment.order, payment)
        return render(request, 'shop/success.html', {'order': payment.order})
    payment.status = 'failed'
    payment.callback_payload = {**payment.callback_payload, 'verify_error': result.message}
    payment.save(update_fields=['status', 'callback_payload'])
    _release_coupon_reservation(payment)
    payment.order.status = 'cancelled'
    payment.order.save(update_fields=['status'])
    messages.error(request, result.message or 'پرداخت تأیید نشد.')
    return redirect('checkout')

import secrets
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from .models import CartItem, Order, OrderItem, Entitlement, WalletTransaction, Coupon, Referral
from books.models import Book
from accounts.models import User
from gamification.services import purchase_points_for_amount, add_points
from gamification.models import PointLedger

REFERRAL_REWARD = Decimal('50000')


def reward_referral(invitee):
    referral = Referral.objects.select_related('inviter').filter(
        invitee=invitee, rewarded=False
    ).first()
    if not referral:
        return False
    inviter = User.objects.select_for_update().get(pk=referral.inviter_id)
    inviter.wallet_balance += REFERRAL_REWARD
    invitee.wallet_balance += REFERRAL_REWARD
    inviter.save(update_fields=['wallet_balance'])
    invitee.save(update_fields=['wallet_balance'])
    WalletTransaction.objects.create(
        user=inviter, amount=REFERRAL_REWARD, type='reward',
        reason='جایزه معرفی دوست',
    )
    WalletTransaction.objects.create(
        user=invitee, amount=REFERRAL_REWARD, type='reward',
        reason='جایزه ثبت‌نام با معرفی دوست',
    )
    referral.rewarded = True
    referral.save(update_fields=['rewarded'])
    return True


def _tracking_code():
    for _ in range(30):
        code = f'{secrets.randbelow(1000000):06d}'
        if not Order.objects.filter(tracking_code=code).exists():
            return code
    raise RuntimeError('Could not generate tracking code')


@login_required
def cart(request):
    if request.method == 'POST':
        book = Book.objects.filter(pk=request.POST.get('book_id')).first()
        if book and not Entitlement.objects.filter(user=request.user, book=book).exists():
            CartItem.objects.get_or_create(user=request.user, book=book)
        return redirect('cart')
    items = CartItem.objects.filter(user=request.user).select_related('book')
    owned_ids = list(Entitlement.objects.filter(user=request.user, book__in=[i.book for i in items]).values_list('book_id', flat=True))
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
    items = [i for i in CartItem.objects.filter(user=request.user).select_related('book') if not Entitlement.objects.filter(user=request.user, book=i.book).exists()]
    if not items:
        CartItem.objects.filter(user=request.user).delete()
        return redirect('cart')
    subtotal = sum((item.book.price for item in items), Decimal(0))
    discount = Decimal(0)
    coupon = None
    if request.method == 'POST':
        raw = request.POST.get('coupon', '').strip().upper()
        if raw:
            coupon = Coupon.objects.filter(code=raw).first()
            if not coupon or not coupon.active:
                messages.error(request, 'کد تخفیف معتبر نیست.')
                return redirect('checkout')
            if coupon.expires_at and coupon.expires_at <= timezone.now():
                messages.error(request, 'این کد منقضی شده است.')
                return redirect('checkout')
            if coupon.used >= coupon.capacity or subtotal < coupon.min_order:
                messages.error(request, 'شرایط استفاده از این کد رعایت نشده است.')
                return redirect('checkout')
            discount = min(subtotal * coupon.percent / 100 if coupon.percent else coupon.amount, subtotal)
        tax = ((subtotal - discount) * Decimal('0.10')).quantize(Decimal('1'))
        total = subtotal - discount + tax
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            if user.wallet_balance < total:
                messages.error(request, 'موجودی کیف پول کافی نیست.')
                return redirect('checkout')
            if coupon:
                locked_coupon = Coupon.objects.select_for_update().get(pk=coupon.pk)
                if not locked_coupon.active or locked_coupon.used >= locked_coupon.capacity or (locked_coupon.expires_at and locked_coupon.expires_at <= timezone.now()):
                    messages.error(request, 'کد تخفیف دیگر قابل استفاده نیست.')
                    return redirect('checkout')
                locked_coupon.used = F('used') + 1
                locked_coupon.save(update_fields=['used'])
                discount = min(subtotal * locked_coupon.percent / 100 if locked_coupon.percent else locked_coupon.amount, subtotal)
                tax = ((subtotal - discount) * Decimal('0.10')).quantize(Decimal('1'))
                total = subtotal - discount + tax
                if user.wallet_balance < total:
                    messages.error(request, 'موجودی کیف پول کافی نیست.')
                    return redirect('checkout')
            user.wallet_balance -= total
            user.save(update_fields=['wallet_balance'])
            order = Order.objects.create(user=user, subtotal=subtotal, discount=discount, tax=tax, total=total, status='paid', tracking_code=_tracking_code())
            OrderItem.objects.bulk_create([OrderItem(order=order, book=i.book, price=i.book.price) for i in items])
            Entitlement.objects.bulk_create([Entitlement(user=user, book=i.book, order=order) for i in items], ignore_conflicts=True)
            WalletTransaction.objects.create(user=user, amount=total, type='debit', reason='خرید کتاب', order=order)
            add_points(user, PointLedger.PURCHASE, purchase_points_for_amount(total), 'امتیاز خرید', reference=f'order:{order.id}')
            reward_referral(user)
            CartItem.objects.filter(user=user).delete()
        return render(request, 'shop/success.html', {'order': order})
    tax = (subtotal * Decimal('.10')).quantize(Decimal('1'))
    return render(request, 'shop/checkout.html', {'subtotal': subtotal, 'discount': discount, 'tax': tax, 'total': subtotal + tax})


@login_required
def order_detail(request, tracking_code):
    order = get_object_or_404(Order.objects.prefetch_related('items__book'), tracking_code=tracking_code, user=request.user)
    return render(request, 'shop/order_detail.html', {'order': order})


@login_required
def wallet(request):
    transactions = WalletTransaction.objects.filter(user=request.user).select_related('order').order_by('-created_at')[:50]
    return render(request, 'shop/wallet.html', {'transactions': transactions})

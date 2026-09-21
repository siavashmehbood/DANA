from django.db import models
from django.core.validators import MaxValueValidator
from accounts.models import User
from books.models import Book


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    percent = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    amount = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    capacity = models.PositiveIntegerField(default=1)
    used = models.PositiveIntegerField(default=0)
    min_order = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'book'], name='unique_cart_user_book')]


class Order(models.Model):
    STATUS = [('pending', 'Pending'), ('paid', 'Paid'), ('cancelled', 'Cancelled'), ('gift', 'Gift')]
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    subtotal = models.DecimalField(max_digits=14, decimal_places=0)
    discount = models.DecimalField(max_digits=14, decimal_places=0)
    tax = models.DecimalField(max_digits=14, decimal_places=0)
    total = models.DecimalField(max_digits=14, decimal_places=0)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    tracking_code = models.CharField(max_length=20, unique=True)
    gift_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='received_gifts')
    created_at = models.DateTimeField(auto_now_add=True)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    book = models.ForeignKey(Book, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=14, decimal_places=0)


class Entitlement(models.Model):
    SOURCES = [('purchase','خرید'),('subscription','اشتراک'),('promotion','هدیه/کمپین'),('admin','اعطای مدیر'),('gift','هدیه')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='entitlements')
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)
    source = models.CharField(max_length=20, choices=SOURCES, default='purchase')
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'book'], name='unique_entitlement_user_book')]
        indexes = [models.Index(fields=['user','expires_at'])]


class WalletTransaction(models.Model):
    TYPES = [('credit', 'Credit'), ('debit', 'Debit'), ('refund', 'Refund'), ('reward', 'Reward')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallet_transactions')
    amount = models.DecimalField(max_digits=14, decimal_places=0)
    type = models.CharField(max_length=20, choices=TYPES)
    reason = models.CharField(max_length=250)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)
    balance_before = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    balance_after = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    reference = models.CharField(max_length=120, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CheckoutRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='checkout_requests')
    idempotency_key = models.CharField(max_length=120)
    order = models.OneToOneField(Order, null=True, blank=True, on_delete=models.SET_NULL, related_name='checkout_request')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'idempotency_key'], name='unique_checkout_idempotency')]


class Payment(models.Model):
    STATUS = [('pending', 'Pending'), ('successful', 'Successful'), ('failed', 'Failed'), ('cancelled', 'Cancelled'), ('refunded', 'Refunded')]
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='payments')
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='payments')
    provider = models.CharField(max_length=50, default='wallet')
    authority = models.CharField(max_length=150, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=0)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    callback_payload = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Referral(models.Model):
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals')
    invitee = models.OneToOneField(User, on_delete=models.CASCADE, related_name='invited_by')
    rewarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

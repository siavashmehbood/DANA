from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Coupon, Order, OrderItem, Entitlement, WalletTransaction, Referral, CartItem, CheckoutRequest, Payment

@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ('tracking_code', 'user', 'total', 'tax', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('tracking_code', 'user__username', 'user__phone')
    readonly_fields = ('tracking_code', 'created_at')
    list_per_page = 25

@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = ('code', 'percent', 'amount', 'capacity', 'used', 'active', 'expires_at')
    list_filter = ('active', 'expires_at')
    search_fields = ('code',)

@admin.register(WalletTransaction)
class WalletTransactionAdmin(ModelAdmin):
    list_display = ('user', 'amount', 'type', 'balance_before', 'balance_after', 'reference', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('user__username', 'user__phone', 'reason', 'reference')
    readonly_fields = ('created_at', 'balance_before', 'balance_after', 'reference')

@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ('id', 'user', 'order', 'provider', 'amount', 'status', 'created_at')
    list_filter = ('provider', 'status', 'created_at')
    search_fields = ('authority', 'idempotency_key', 'user__username', 'user__phone')
    readonly_fields = ('created_at', 'updated_at', 'idempotency_key')

@admin.register(CheckoutRequest)
class CheckoutRequestAdmin(ModelAdmin):
    list_display = ('user', 'idempotency_key', 'order', 'created_at')
    search_fields = ('user__username', 'user__phone', 'idempotency_key')
    readonly_fields = ('created_at',)

@admin.register(Entitlement)
class EntitlementAdmin(ModelAdmin):
    list_display = ('user', 'book', 'order', 'granted_at', 'expires_at')
    search_fields = ('user__username', 'user__phone', 'book__name')
    list_filter = ('granted_at', 'expires_at')

@admin.register(CartItem)
class CartItemAdmin(ModelAdmin):
    list_display = ('user', 'book', 'created_at')
    search_fields = ('user__username', 'user__phone', 'book__name')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)

admin.site.register([OrderItem, Referral])

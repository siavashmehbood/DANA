from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Coupon, Order, OrderItem, Entitlement, WalletTransaction, Referral, CartItem, CheckoutRequest, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('book', 'price')
    can_delete = False


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ('tracking_code', 'user', 'subtotal', 'discount', 'tax', 'total', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('tracking_code', 'user__username', 'user__phone')
    readonly_fields = ('user', 'subtotal', 'discount', 'tax', 'total', 'tracking_code', 'created_at')
    list_per_page = 25
    date_hierarchy = 'created_at'
    inlines = (OrderItemInline,)


@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = ('code', 'percent', 'amount', 'min_order', 'capacity', 'used', 'active', 'expires_at')
    list_filter = ('active', 'expires_at')
    search_fields = ('code',)
    list_editable = ('active',)


@admin.register(WalletTransaction)
class WalletTransactionAdmin(ModelAdmin):
    list_display = ('user', 'amount', 'type', 'balance_before', 'balance_after', 'reference', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('user__username', 'user__phone', 'reason', 'reference')
    readonly_fields = ('user', 'amount', 'type', 'reason', 'order', 'created_at', 'balance_before', 'balance_after', 'reference')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ('id', 'user', 'order', 'provider', 'amount', 'status', 'authority', 'created_at')
    list_filter = ('provider', 'status', 'created_at')
    search_fields = ('authority', 'idempotency_key', 'user__username', 'user__phone', 'order__tracking_code')
    readonly_fields = ('user', 'order', 'provider', 'authority', 'amount', 'status', 'callback_payload', 'created_at', 'updated_at', 'idempotency_key')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CheckoutRequest)
class CheckoutRequestAdmin(ModelAdmin):
    list_display = ('user', 'idempotency_key', 'order', 'created_at')
    search_fields = ('user__username', 'user__phone', 'idempotency_key')
    readonly_fields = ('user', 'idempotency_key', 'order', 'created_at')

    def has_add_permission(self, request):
        return False


@admin.register(Entitlement)
class EntitlementAdmin(ModelAdmin):
    list_display = ('user', 'book', 'source', 'order', 'granted_at', 'expires_at')
    search_fields = ('user__username', 'user__phone', 'book__name')
    list_filter = ('source', 'granted_at', 'expires_at')
    autocomplete_fields = ('user', 'book')
    readonly_fields = ('granted_at', 'order')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.source = 'admin'
        super().save_model(request, obj, form, change)


@admin.register(CartItem)
class CartItemAdmin(ModelAdmin):
    list_display = ('user', 'book', 'created_at')
    search_fields = ('user__username', 'user__phone', 'book__name')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)


@admin.register(Referral)
class ReferralAdmin(ModelAdmin):
    list_display = ('inviter', 'invitee', 'rewarded', 'created_at')
    list_filter = ('rewarded', 'created_at')
    search_fields = ('inviter__username', 'inviter__phone', 'invitee__username', 'invitee__phone')
    readonly_fields = ('created_at',)

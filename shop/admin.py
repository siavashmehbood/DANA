from decimal import Decimal
from django import forms
from django.contrib import admin, messages
from django.db import transaction
from .models import Coupon, Order, OrderItem, Entitlement, WalletTransaction, Referral, CartItem

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('tracking_code', 'user', 'total', 'tax', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('tracking_code', 'user__username', 'user__phone')
    readonly_fields = ('tracking_code', 'created_at')
    list_per_page = 25

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'percent', 'amount', 'capacity', 'used', 'active', 'expires_at')
    list_filter = ('active', 'expires_at')
    search_fields = ('code',)

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'type', 'reason', 'order', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('user__username', 'user__phone', 'reason')
    readonly_fields = ('created_at',)

@admin.register(Entitlement)
class EntitlementAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'order', 'granted_at', 'expires_at')
    search_fields = ('user__username', 'user__phone', 'book__name')
    list_filter = ('granted_at', 'expires_at')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'created_at')
    search_fields = ('user__username', 'user__phone', 'book__name')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)

admin.site.register([OrderItem, Referral])

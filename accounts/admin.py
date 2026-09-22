from decimal import Decimal
import secrets

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import transaction

from .models import User, Device, OTPCode, UserSession
from shop.models import WalletTransaction


class UserAdminForm(forms.ModelForm):
    wallet_topup = forms.DecimalField(
        label='شارژ کیف پول',
        min_value=Decimal('0'),
        required=False,
        help_text='فقط مبلغ شارژ را وارد کنید؛ تراکنش به‌صورت خودکار در دفتر کیف پول ثبت می‌شود.',
    )

    class Meta:
        model = User
        fields = '__all__'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserAdminForm
    list_display = (
        'phone', 'full_name', 'wallet_balance', 'xp', 'points',
        'is_active', 'is_staff', 'date_joined',
    )
    list_filter = ('is_active', 'is_staff', 'leaderboard_public', 'is_deactivated')
    search_fields = ('username', 'phone', 'first_name', 'last_name', 'email', 'referral_code')
    readonly_fields = ('referral_code', 'terms_accepted_at', 'wallet_balance', 'last_login', 'date_joined')
    list_per_page = 30
    date_hierarchy = 'date_joined'
    ordering = ('-date_joined',)

    @admin.display(description='نام کاربر')
    def full_name(self, obj):
        return obj.get_full_name() or obj.phone or obj.username

    fieldsets = (
        ('اطلاعات حساب', {
            'fields': ('username', 'phone', 'email', 'first_name', 'last_name', 'avatar'),
        }),
        ('وضعیت و دسترسی', {
            'fields': ('is_active', 'is_deactivated', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('مالی و امتیاز', {
            'fields': ('wallet_balance', 'wallet_topup', 'xp', 'points', 'purchase_points', 'study_points'),
        }),
        ('دعوت و قوانین', {
            'fields': ('referral_code', 'leaderboard_public', 'terms_accepted_at'),
        }),
        ('امنیت و ورود', {
            'fields': ('password', 'last_login', 'date_joined'),
        }),
    )
    add_fieldsets = (
        ('ساخت کاربر', {
            'classes': ('wide',),
            'fields': ('phone', 'username', 'password1', 'password2', 'is_active', 'is_staff'),
        }),
    )

    def save_model(self, request, obj, form, change):
        topup = form.cleaned_data.get('wallet_topup') or Decimal('0')
        if not change:
            obj.save()
            return
        with transaction.atomic():
            locked = User.objects.select_for_update().get(pk=obj.pk)
            if topup > 0:
                balance_before = locked.wallet_balance
                locked.wallet_balance += topup
                locked.save(update_fields=['wallet_balance'])
                WalletTransaction.objects.create(
                    user=locked,
                    amount=topup,
                    type='credit',
                    reason=f'شارژ توسط مدیر: {request.user.username}',
                    balance_before=balance_before,
                    balance_after=locked.wallet_balance,
                    reference=f'admin-topup:{request.user.pk}:{obj.pk}:{secrets.token_hex(8)}',
                )
                messages.success(request, f'{topup:,.0f} تومان به کیف پول کاربر اضافه شد.')
            obj.wallet_balance = locked.wallet_balance
            super().save_model(request, obj, form, change)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'last_seen', 'created_at')
    search_fields = ('user__username', 'user__phone', 'name')
    list_filter = ('last_seen',)
    readonly_fields = ('token', 'created_at', 'last_seen')
    date_hierarchy = 'last_seen'


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ('phone', 'purpose', 'expires_at', 'attempts', 'used', 'created_at')
    list_filter = ('purpose', 'used', 'created_at')
    search_fields = ('phone',)
    exclude = ('code',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device', 'ip', 'last_seen', 'created_at')
    search_fields = ('user__username', 'user__phone', 'ip')
    list_filter = ('last_seen', 'created_at')
    readonly_fields = ('session_key', 'user_agent', 'ip', 'created_at', 'last_seen')
    date_hierarchy = 'last_seen'

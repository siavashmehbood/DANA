from decimal import Decimal
from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import transaction
from .models import User, Device, OTPCode, UserSession
from shop.models import WalletTransaction

class UserAdminForm(forms.ModelForm):
    wallet_topup = forms.DecimalField(
        label='شارژ کیف پول', min_value=Decimal('0'), required=False,
        help_text='برای شارژ حساب مبلغ را وارد کنید؛ این مبلغ در دفتر تراکنش نیز ثبت می‌شود.'
    )

    class Meta:
        model = User
        fields = '__all__'

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserAdminForm
    list_display = ('username', 'phone', 'wallet_balance', 'xp', 'points', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'leaderboard_public')
    search_fields = ('username', 'phone', 'first_name', 'last_name', 'email')
    readonly_fields = ('referral_code', 'terms_accepted_at', 'wallet_balance')
    list_per_page = 30

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        if obj:
            title, options = fieldsets[-1]
            fields = list(options.get('fields', ()))
            if 'wallet_topup' not in fields:
                fields.append('wallet_topup')
            fieldsets[-1] = (title, {**options, 'fields': tuple(fields)})
        return tuple(fieldsets)

    def save_model(self, request, obj, form, change):
        topup = form.cleaned_data.get('wallet_topup') or Decimal('0')
        if not change:
            obj.save()
            return
        with transaction.atomic():
            locked = User.objects.select_for_update().get(pk=obj.pk)
            if topup > 0:
                locked.wallet_balance += topup
                locked.save(update_fields=['wallet_balance'])
                WalletTransaction.objects.create(
                    user=locked, amount=topup, type='credit',
                    reason=f'شارژ توسط مدیر: {request.user.username}',
                )
                messages.success(request, f'{topup:,.0f} تومان به کیف پول کاربر اضافه شد.')
            obj.wallet_balance = locked.wallet_balance
            super().save_model(request, obj, form, change)

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'last_seen', 'created_at')
    search_fields = ('user__username', 'user__phone', 'name')
    list_filter = ('last_seen',)

@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ('phone', 'purpose', 'code', 'expires_at', 'attempts', 'used', 'created_at')
    list_filter = ('purpose', 'used', 'created_at')
    search_fields = ('phone',)
    readonly_fields = ('created_at',)

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device', 'ip', 'last_seen', 'created_at')
    search_fields = ('user__username', 'user__phone', 'ip')
    list_filter = ('last_seen', 'created_at')

from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Notification, PushSubscription, EmailLog

@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display=('title','user','kind','read_at','created_at')
    list_filter=('kind','read_at','created_at')
    search_fields=('title','body','user__username','user__phone')
    autocomplete_fields=('user',)
    readonly_fields=('created_at',)
    list_per_page=50

@admin.register(PushSubscription)
class PushSubscriptionAdmin(ModelAdmin):
    list_display=('user','created_at')
    search_fields=('user__username','user__phone','endpoint')
    readonly_fields=('endpoint','p256dh','auth','created_at')
    list_per_page=50
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False

@admin.register(EmailLog)
class EmailLogAdmin(ModelAdmin):
    list_display=('email','subject','status_fa','created_at')
    list_filter=('status','created_at')
    search_fields=('email','subject','user__username','user__phone')
    readonly_fields=('user','email','subject','status','created_at')
    list_per_page=50

    @admin.display(description='وضعیت')
    def status_fa(self,obj):
        return {'queued':'در صف','sent':'ارسال‌شده','delivered':'تحویل‌شده','failed':'ناموفق'}.get(obj.status,obj.status)

    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False

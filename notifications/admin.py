from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Notification,PushSubscription,EmailLog
admin.site.register([Notification,PushSubscription,EmailLog])

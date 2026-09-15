from django.contrib import admin
from .models import Notification,PushSubscription,EmailLog
admin.site.register([Notification,PushSubscription,EmailLog])

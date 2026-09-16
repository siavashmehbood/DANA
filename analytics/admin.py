from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Event
admin.site.register(Event)

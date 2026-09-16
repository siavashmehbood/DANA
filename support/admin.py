from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Ticket,TicketMessage
admin.site.register([Ticket,TicketMessage])

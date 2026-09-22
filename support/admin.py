from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Ticket, TicketMessage
class TicketMessageInline(admin.TabularInline):
    model=TicketMessage
    extra=0
    fields=('user','body','created_at')
    readonly_fields=('created_at',)
    autocomplete_fields=('user',)
@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    list_display=('subject','user','status','priority','category','assigned_to','updated_at')
    list_filter=('status','priority','category','updated_at')
    search_fields=('subject','body','user__username','user__phone')
    autocomplete_fields=('user','assigned_to')
    list_editable=('status','priority')
    readonly_fields=('created_at','updated_at')
    date_hierarchy='created_at'
    inlines=(TicketMessageInline,)
@admin.register(TicketMessage)
class TicketMessageAdmin(ModelAdmin):
    list_display=('ticket','user','created_at')
    search_fields=('ticket__subject','user__username','user__phone','body')
    autocomplete_fields=('ticket','user')
    readonly_fields=('created_at',)

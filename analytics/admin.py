from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Event
@admin.register(Event)
class EventAdmin(ModelAdmin):
    list_display=('name','user','book','value','session_key','created_at'); list_filter=('name','created_at'); search_fields=('name','user__username','user__phone','book__name'); readonly_fields=('user','book','name','value','metadata','created_at'); date_hierarchy='created_at'
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False

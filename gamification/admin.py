from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import (
    GamificationLevel, Badge, UserBadge, XPEvent, PointLedger,
    Mission, UserMission, UserStreak, HallOfFameRecord,
)

@admin.register(GamificationLevel)
class GamificationLevelAdmin(ModelAdmin):
    list_display = ('name', 'order', 'min_xp', 'active')
    list_filter = ('active',)
    ordering = ('order', 'min_xp')

@admin.register(Badge)
class BadgeAdmin(ModelAdmin):
    list_display = ('name', 'tier', 'xp_reward', 'active')
    list_filter = ('tier', 'active')
    search_fields = ('name', 'description')

@admin.register(XPEvent)
class XPEventAdmin(ModelAdmin):
    list_display = ('user', 'amount', 'reason', 'source', 'reference', 'created_at')
    list_filter = ('source', 'created_at')
    search_fields = ('user__username', 'user__phone', 'reason', 'reference')
    readonly_fields = ('user', 'amount', 'reason', 'source', 'reference', 'created_at')
    date_hierarchy = 'created_at'
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(PointLedger)
class PointLedgerAdmin(ModelAdmin):
    list_display = ('user', 'point_type', 'amount', 'reason', 'revoked', 'created_at')
    list_filter = ('point_type', 'revoked', 'created_at')
    search_fields = ('user__username', 'user__phone', 'reason', 'reference')
    readonly_fields = ('user', 'point_type', 'amount', 'reason', 'book', 'reference', 'revoked', 'created_at')
    date_hierarchy = 'created_at'
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(Mission)
class MissionAdmin(ModelAdmin):
    list_display = ('title', 'period', 'target', 'xp_reward', 'study_points_reward', 'active')
    list_filter = ('period', 'active')
    search_fields = ('title', 'description')

@admin.register(UserBadge)
class UserBadgeAdmin(ModelAdmin):
    list_display=('user','badge','earned_at')
    readonly_fields=('user','badge','earned_at')
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(UserMission)
class UserMissionAdmin(ModelAdmin):
    list_display=('user','mission','progress','period_key','completed_at')
    readonly_fields=('user','mission','progress','period_key','completed_at')
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(UserStreak)
class UserStreakAdmin(ModelAdmin):
    list_display=('user','current_days','longest_days','last_activity_date')
    readonly_fields=('user','current_days','longest_days','last_activity_date')
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(HallOfFameRecord)
class HallOfFameRecordAdmin(ModelAdmin):
    list_display=('user','category','value','period','created_at')
    readonly_fields=('user','category','value','period','created_at')
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

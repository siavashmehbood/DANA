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
    list_display = ('user', 'amount', 'reason', 'source', 'created_at')
    list_filter = ('source', 'created_at')
    search_fields = ('user__username', 'user__phone', 'reason')

@admin.register(PointLedger)
class PointLedgerAdmin(ModelAdmin):
    list_display = ('user', 'point_type', 'amount', 'reason', 'revoked', 'created_at')
    list_filter = ('point_type', 'revoked', 'created_at')
    search_fields = ('user__username', 'user__phone', 'reason', 'reference')

@admin.register(Mission)
class MissionAdmin(ModelAdmin):
    list_display = ('title', 'period', 'target', 'xp_reward', 'study_points_reward', 'active')
    list_filter = ('period', 'active')
    search_fields = ('title', 'description')

admin.site.register([UserBadge, UserMission, UserStreak, HallOfFameRecord])

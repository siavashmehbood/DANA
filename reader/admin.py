from django.contrib import admin
from unfold.admin import ModelAdmin

from gamification.services import add_points, study_points_for_score
from .models import ReadingProgress, AudioProgress, ReadingGoal, Bookmark, Highlight, Note, ProblemReport, Review


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ('book', 'user', 'rating', 'admin_score', 'approved', 'created_at')
    list_filter = ('approved', 'admin_score', 'rating')
    search_fields = ('book__name', 'user__username', 'text')
    list_editable = ('admin_score', 'approved')

    def save_model(self, request, obj, form, change):
        previous_score = None
        if change and obj.pk:
            previous_score = Review.objects.filter(pk=obj.pk).values_list(
                'admin_score', flat=True
            ).first()
        super().save_model(request, obj, form, change)
        if obj.admin_score and obj.admin_score != previous_score:
            add_points(
                obj.user,
                'study',
                study_points_for_score(obj.admin_score),
                'امتیاز مطالعه از ارزیابی مدیر',
                book=obj.book,
                reference=f'review:{obj.pk}',
            )


@admin.register(ReadingGoal)
class ReadingGoalAdmin(ModelAdmin):
    list_display=('user','weekly_minutes','weekly_books','updated_at')
    search_fields=('user__username','user__phone')

@admin.register(ReadingProgress)
class ReadingProgressAdmin(ModelAdmin):
    list_display=('user','book','progress','current_page','current_chapter','updated_at')
    list_filter=('updated_at',)
    search_fields=('user__username','user__phone','book__name')
    readonly_fields=('user','book','progress','current_page','current_chapter','seconds','audio_seconds','updated_at')
    date_hierarchy='updated_at'
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(Bookmark)
class BookmarkAdmin(ModelAdmin):
    list_display=('user','book','page','title','created_at')
    search_fields=('user__username','user__phone','book__name','title')
    readonly_fields=('user','book','page','title','created_at')
    def has_add_permission(self, request): return False

@admin.register(Highlight)
class HighlightAdmin(ModelAdmin):
    list_display=('user','book','page','color','created_at')
    list_filter=('color','created_at')
    search_fields=('user__username','user__phone','book__name','text')
    readonly_fields=('user','book','page','text','color','created_at')
    def has_add_permission(self, request): return False

@admin.register(Note)
class NoteAdmin(ModelAdmin):
    list_display=('user','book','page','created_at')
    search_fields=('user__username','user__phone','book__name','text')
    readonly_fields=('user','book','page','text','created_at')
    def has_add_permission(self, request): return False

@admin.register(AudioProgress)
class AudioProgressAdmin(ModelAdmin):
    list_display=('user','book','chapter','position_seconds','duration_seconds','completed','updated_at')
    list_filter=('completed','updated_at')
    search_fields=('user__username','user__phone','book__name','chapter__title')
    readonly_fields=('user','book','chapter','position_seconds','duration_seconds','completed','updated_at')
    date_hierarchy='updated_at'
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(ProblemReport)
class ProblemReportAdmin(ModelAdmin):
    list_display=('book','user','status','created_at')
    list_filter=('status','created_at')
    search_fields=('book__name','user__username','user__phone','text')
    list_editable=('status',)
    autocomplete_fields=('book','user')
    readonly_fields=('created_at',)

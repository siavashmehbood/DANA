from django.contrib import admin
from unfold.admin import ModelAdmin

from gamification.services import add_points, study_points_for_score
from .models import ReadingProgress, ReadingGoal, Bookmark, Highlight, Note, ProblemReport, Review


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

admin.site.register([ReadingProgress, Bookmark, Highlight, Note])

@admin.register(ProblemReport)
class ProblemReportAdmin(ModelAdmin):
    list_display=('book','user','status','created_at')
    list_filter=('status','created_at')
    search_fields=('book__name','user__username','user__phone','text')
    list_editable=('status',)
    autocomplete_fields=('book','user')
    readonly_fields=('created_at',)

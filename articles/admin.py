from django.contrib import admin
from django.utils import timezone

from .models import Article, ArticleCategory
from .translation import extract_pdf_text


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.action(description='استخراج متن PDF برای مطالعه آنلاین')
def extract_full_text(modeladmin, request, queryset):
    success = 0
    for article in queryset.filter(pdf__isnull=False):
        try:
            text = extract_pdf_text(article)
        except Exception:
            continue
        if text:
            article.full_text = text
            article.updated_at = timezone.now()
            article.save(update_fields=['full_text', 'updated_at'])
            success += 1
    modeladmin.message_user(request, f'متن {success} مقاله استخراج شد.')


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'year', 'category', 'published', 'featured',
        'translation_status', 'text_status', 'translated_at',
    )
    list_filter = (
        'published', 'featured', 'access', 'category',
        'year', 'translation_status',
    )
    search_fields = (
        'title', 'title_fa', 'authors', 'abstract',
        'abstract_fa', 'doi', 'journal',
    )
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('featured', 'published')
    readonly_fields = ('downloads', 'created_at', 'updated_at', 'translated_at')
    actions = (extract_full_text,)

    @admin.display(description='متن')
    def text_status(self, obj):
        if obj.full_text_fa:
            return 'ترجمه آماده'
        if obj.full_text:
            return 'متن استخراج شده؛ ترجمه در حال پردازش'
        if obj.pdf_url:
            return 'PDF در صف دریافت'
        return 'فقط چکیده'

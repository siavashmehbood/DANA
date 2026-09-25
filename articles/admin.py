from django.contrib import admin
from unfold.admin import ModelAdmin
from django.utils import timezone
from django.db import transaction
from django.db.models import Max, Q

from .models import Article, ArticleCategory, ArticleSource, ArticleTranslationVersion
from .translation import extract_pdf_text, translate_article


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ArticleSource)
class ArticleSourceAdmin(ModelAdmin):
    list_display = ('name', 'source_type', 'is_active', 'allow_full_republish', 'attribution_required')
    list_filter = ('source_type', 'is_active', 'allow_full_republish')
    search_fields = ('name', 'base_url', 'feed_url')


@admin.register(ArticleTranslationVersion)
class ArticleTranslationVersionAdmin(ModelAdmin):
    list_display = ('article', 'version', 'provider', 'quality_score', 'is_valid', 'created_at')
    list_filter = ('is_valid', 'provider')
    search_fields = ('article__title', 'article__title_fa', 'provider')
    readonly_fields = ('article', 'version', 'title_fa', 'abstract_fa', 'content_fa', 'provider', 'quality_score', 'source_hash', 'is_valid', 'error', 'created_by', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.action(description='ترجمه/بازترجمه مقاله‌های انتخاب‌شده')
def retranslate_articles(modeladmin, request, queryset):
    success = failed = 0
    for article in queryset:
        before = article.translation_version
        try:
            translate_article(article, full_text=bool(article.full_text or article.pdf), force=True, provider='admin', created_by=request.user)
        except Exception as exc:
            article.translation_status = 'failed'
            article.translation_error = str(exc)[:4000]
            article.save(update_fields=['translation_status', 'translation_error', 'updated_at'])
        article.refresh_from_db()
        if article.translation_version > before:
            success += 1
        else:
            failed += 1
    modeladmin.message_user(request, f'{success} ترجمه جدید ثبت شد؛ {failed} مورد ناموفق بود.')


@admin.action(description='بازگردانی به آخرین ترجمه سالم قبلی')
def rollback_translation(modeladmin, request, queryset):
    restored = 0
    for article in queryset:
        version = article.translation_versions.filter(is_valid=True, version__lt=article.translation_version).order_by('-version').first()
        if not version:
            continue
        with transaction.atomic():
            locked = Article.objects.select_for_update().get(pk=article.pk)
            next_version = (locked.translation_versions.aggregate(max_version=Max('version'))['max_version'] or 0) + 1
            locked.title_fa = version.title_fa
            locked.abstract_fa = version.abstract_fa
            locked.full_text_fa = version.content_fa
            locked.translation_hash = version.source_hash
            locked.translation_version = next_version
            locked.translation_quality = version.quality_score
            locked.translation_status = 'reviewed'
            locked.translation_error = ''
            locked.translated_at = timezone.now()
            locked.save()
            ArticleTranslationVersion.objects.create(
                article=locked, version=next_version, title_fa=version.title_fa,
                abstract_fa=version.abstract_fa, content_fa=version.content_fa,
                provider='rollback', quality_score=version.quality_score,
                source_hash=version.source_hash, is_valid=True, created_by=request.user,
            )
        restored += 1
    modeladmin.message_user(request, f'{restored} مقاله به ترجمه سالم قبلی بازگردانده شد.')


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


class TranslationBacklogFilter(admin.SimpleListFilter):
    title='سلامت ترجمه'
    parameter_name='translation_health'
    def lookups(self,request,model_admin):
        return (('backlog','نیازمند ترجمه/ترمیم'),('healthy','ترجمه سالم'))
    def queryset(self,request,queryset):
        backlog=Q(translation_status__in=['not_requested','pending','failed','provider_failed','validation_failed','retry_pending','translating'])|Q(title_fa='')|Q(abstract__gt='',abstract_fa='')|Q(full_text__gt='',full_text_fa='',source__allow_full_republish=True)
        if self.value()=='backlog': return queryset.filter(backlog).distinct()
        if self.value()=='healthy': return queryset.exclude(backlog).distinct()
        return queryset


@admin.register(Article)
class ArticleAdmin(ModelAdmin):
    list_display = ('title', 'year', 'category', 'source', 'published', 'featured', 'translation_status', 'translation_health', 'translation_version', 'text_status', 'translated_at')
    list_filter = (TranslationBacklogFilter, 'published', 'featured', 'access', 'category', 'source', 'year', 'translation_status')
    search_fields = ('title', 'title_fa', 'authors', 'abstract', 'abstract_fa', 'doi', 'journal', 'source_url')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('featured', 'published')
    readonly_fields = ('downloads', 'created_at', 'updated_at', 'translated_at', 'translation_hash', 'translation_version', 'translation_error')
    autocomplete_fields = ('category', 'source')
    actions = (extract_full_text, retranslate_articles, rollback_translation)
    fieldsets = (
        ('اصل مقاله — همیشه حفظ شود', {'fields': ('title', 'authors', 'original_language', 'abstract', 'full_text', 'source', 'source_provider', 'source_url', 'publication_date', 'retrieved_at', 'journal', 'doi')}),
        ('نسخه فارسی', {'fields': ('title_fa', 'abstract_fa', 'full_text_fa', 'translation_status', 'translation_version', 'translation_quality', 'translation_error', 'translation_hash', 'translated_at')}),
        ('انتشار و طبقه‌بندی', {'fields': ('slug', 'category', 'access', 'featured', 'published', 'cover', 'pdf', 'pdf_url')}),
        ('اطلاعات سیستمی', {'fields': ('external_id', 'citation_count', 'relevance_score', 'last_discovered_at', 'downloads', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description='سلامت ترجمه')
    def translation_health(self,obj):
        if obj.translation_status in {'not_requested','failed','provider_failed','validation_failed','retry_pending','translating','pending'}:
            return 'نیازمند ترجمه'
        if not obj.title_fa or (obj.abstract and not obj.abstract_fa) or (obj.full_text and not obj.full_text_fa and (not obj.source or obj.source.allow_full_republish)):
            return 'ترجمه ناقص'
        return 'سالم'

    @admin.display(description='متن')
    def text_status(self, obj):
        if obj.full_text_fa:
            return 'ترجمه آماده'
        if obj.translation_status in {'failed','provider_failed','validation_failed'}:
            return 'ترجمه ناموفق؛ اصل مقاله محفوظ است'
        if obj.translation_status == 'retry_pending':
            return 'ترجمه در صف تلاش مجدد'
        if obj.translation_status == 'original_only':
            return 'فقط اصل مقاله؛ ترجمه کامل منتشر نشده'
        if obj.full_text:
            return 'اصل مقاله آماده؛ ترجمه در انتظار'
        if obj.pdf_url:
            return 'PDF در صف دریافت'
        return 'فقط چکیده'

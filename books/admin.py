from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Author, Category, Level, Book, Chapter, MediaAsset


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    fields = ('order', 'title', 'text', 'audio', 'duration')
    ordering = ('order',)


@admin.register(Book)
class BookAdmin(ModelAdmin):
    actions = ('publish_selected','unpublish_selected','feature_selected','unfeature_selected')
    readonly_fields = ('created_at','updated_at')
    list_display = ('name', 'author', 'category', 'price', 'old_price', 'status', 'visibility', 'featured', 'subscription_included', 'publish_at', 'has_pdf', 'has_audio')
    list_select_related = ('author','category','level')
    date_hierarchy = 'created_at'
    list_filter = ('status', 'visibility', 'featured', 'subscription_included', 'category', 'level')
    search_fields = ('name', 'slug', 'author__name', 'summary', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 25
    autocomplete_fields = ('author', 'category', 'level')
    list_editable = ('status', 'featured', 'subscription_included')
    inlines = (ChapterInline,)
    fieldsets = (
        ('مشخصات کتاب', {'fields': ('name', 'slug', 'author', 'category', 'level', 'cover', 'summary', 'description')}),
        ('فروش', {'fields': ('price', 'old_price', 'preview_percent')}),
        ('فایل و رسانه', {'fields': ('pdf', 'audio')}),
        ('انتشار و دسترسی', {'fields': ('status', 'publish_at', 'visibility', 'featured', 'subscription_included', 'access_password')}),
        ('اطلاعات سیستمی', {'fields': ('created_at','updated_at'), 'classes': ('collapse',)}),
    )

    @admin.action(description='افزودن به پیشنهادهای ویژه')
    def feature_selected(self, request, queryset):
        queryset.update(featured=True)

    @admin.action(description='حذف از پیشنهادهای ویژه')
    def unfeature_selected(self, request, queryset):
        queryset.update(featured=False)

    @admin.action(description='انتشار کتاب‌های انتخاب‌شده')
    def publish_selected(self, request, queryset):
        valid=queryset.exclude(visibility='password',access_password='')
        updated=valid.update(status='published', publish_at=None)
        skipped=queryset.count()-updated
        if skipped:
            self.message_user(request, f'{skipped} کتاب با وضعیت دسترسی/انتشار نامعتبر منتشر نشد.', level='warning')

    @admin.action(description='بازگرداندن کتاب‌های انتخاب‌شده به پیش‌نویس')
    def unpublish_selected(self, request, queryset):
        queryset.update(status='draft', publish_at=None)

    @admin.display(boolean=True, description='PDF')
    def has_pdf(self, obj):
        return bool(obj.pdf)

    @admin.display(boolean=True, description='صوت')
    def has_audio(self, obj):
        return bool(obj.audio)


@admin.register(Author)
class AuthorAdmin(ModelAdmin):
    list_display = ('name', 'book_count')
    search_fields = ('name', 'bio')
    @admin.display(description='تعداد کتاب')
    def book_count(self, obj):
        return obj.books.count()


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'parent', 'slug')
    list_filter = ('parent',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Level)
class LevelAdmin(ModelAdmin):
    list_display = ('name', 'order', 'min_xp')
    search_fields = ('name',)
    ordering = ('order',)


@admin.register(Chapter)
class ChapterAdmin(ModelAdmin):
    list_display = ('title', 'book', 'order', 'duration', 'has_text', 'has_audio')
    list_select_related = ('book',)
    list_filter = ('book',)
    search_fields = ('title', 'book__name')
    ordering = ('book', 'order')
    list_per_page = 50
    autocomplete_fields = ('book',)

    @admin.display(boolean=True, description='متن')
    def has_text(self, obj):
        return bool(obj.text and obj.text.strip())

    @admin.display(boolean=True, description='فایل صوتی')
    def has_audio(self, obj):
        return bool(obj.audio)


@admin.register(MediaAsset)
class MediaAssetAdmin(ModelAdmin):
    list_display = ('title', 'kind', 'created_at')
    date_hierarchy = 'created_at'
    list_filter = ('kind', 'created_at')
    search_fields = ('title', 'kind')
    readonly_fields = ('created_at',)
    list_per_page = 50

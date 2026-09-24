from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Author, Category, Level, Book, Chapter, MediaAsset


@admin.register(Book)
class BookAdmin(ModelAdmin):
    list_display = ('book_name', 'book_author', 'book_category', 'price_view', 'status_view', 'visibility_view', 'publish_at_view')
    list_filter = ('status', 'visibility', 'category', 'level')
    search_fields = ('name', 'slug', 'author__name', 'summary', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 25
    date_hierarchy = 'created_at'
    autocomplete_fields = ('author', 'category', 'level')
    list_select_related = ('author', 'category', 'level')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('اطلاعات کتاب', {'fields': ('name', 'slug', 'author', 'category', 'level', 'summary', 'description')}),
        ('فروش و دسترسی', {'fields': ('price', 'old_price', 'visibility', 'access_password')}),
        ('فایل‌ها', {'fields': ('cover', 'pdf', 'audio')}),
        ('انتشار', {'fields': ('status', 'publish_at', 'preview_percent')}),
        ('زمان‌بندی', {'fields': ('created_at', 'updated_at')}),
    )

    @admin.display(description='کتاب', ordering='name')
    def book_name(self, obj):
        return obj.name

    @admin.display(description='نویسنده', ordering='author__name')
    def book_author(self, obj):
        return obj.author

    @admin.display(description='دسته‌بندی', ordering='category__name')
    def book_category(self, obj):
        return obj.category or '—'

    @admin.display(description='قیمت', ordering='price')
    def price_view(self, obj):
        return f'{obj.price:,.0f} تومان'

    @admin.display(description='وضعیت', ordering='status')
    def status_view(self, obj):
        return obj.get_status_display()

    @admin.display(description='دسترسی', ordering='visibility')
    def visibility_view(self, obj):
        return obj.get_visibility_display()

    @admin.display(description='انتشار', ordering='publish_at')
    def publish_at_view(self, obj):
        return obj.publish_at or '—'


@admin.register(Author)
class AuthorAdmin(ModelAdmin):
    list_display = ('name', 'book_count')
    search_fields = ('name', 'bio')
    list_per_page = 30

    @admin.display(description='تعداد کتاب')
    def book_count(self, obj):
        return obj.books.count()


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'parent', 'slug', 'book_count')
    list_filter = ('parent',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ('parent',)

    @admin.display(description='تعداد کتاب')
    def book_count(self, obj):
        return obj.book_set.count()


@admin.register(Level)
class LevelAdmin(ModelAdmin):
    list_display = ('name', 'order', 'min_xp')
    search_fields = ('name',)
    ordering = ('order',)
    list_editable = ('order', 'min_xp')


@admin.register(Chapter)
class ChapterAdmin(ModelAdmin):
    list_display = ('title', 'book', 'order', 'duration')
    list_filter = ('book',)
    search_fields = ('title', 'book__name')
    ordering = ('book', 'order')
    autocomplete_fields = ('book',)
    list_select_related = ('book',)


@admin.register(MediaAsset)
class MediaAssetAdmin(ModelAdmin):
    list_display = ('title', 'kind', 'created_at')
    list_filter = ('kind', 'created_at')
    search_fields = ('title', 'kind')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

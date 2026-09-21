from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Author, Category, Level, Book, Chapter, MediaAsset


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    fields = ('order', 'title', 'audio', 'duration')
    ordering = ('order',)


@admin.register(Book)
class BookAdmin(ModelAdmin):
    list_display = ('name', 'author', 'category', 'price', 'old_price', 'status', 'visibility', 'publish_at', 'has_pdf', 'has_audio')
    list_filter = ('status', 'visibility', 'category', 'level')
    search_fields = ('name', 'author__name', 'summary', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 25
    autocomplete_fields = ('author', 'category', 'level')
    list_editable = ('status',)
    inlines = (ChapterInline,)
    fieldsets = (
        ('مشخصات کتاب', {'fields': ('name', 'slug', 'author', 'category', 'level', 'cover', 'summary', 'description')}),
        ('فروش', {'fields': ('price', 'old_price', 'preview_percent')}),
        ('فایل و رسانه', {'fields': ('pdf', 'audio')}),
        ('انتشار و دسترسی', {'fields': ('status', 'publish_at', 'visibility', 'access_password')}),
    )

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
    list_display = ('title', 'book', 'order', 'duration', 'has_audio')
    list_filter = ('book',)
    search_fields = ('title', 'book__name')
    ordering = ('book', 'order')
    autocomplete_fields = ('book',)

    @admin.display(boolean=True, description='فایل صوتی')
    def has_audio(self, obj):
        return bool(obj.audio)


@admin.register(MediaAsset)
class MediaAssetAdmin(ModelAdmin):
    list_display = ('title', 'kind', 'created_at')
    list_filter = ('kind', 'created_at')
    search_fields = ('title', 'kind')
    readonly_fields = ('created_at',)

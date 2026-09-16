from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Author, Category, Level, Book, Chapter, MediaAsset

@admin.register(Book)
class BookAdmin(ModelAdmin):
    list_display = ('name', 'author', 'category', 'price', 'status', 'visibility', 'publish_at')
    list_filter = ('status', 'visibility', 'category', 'level')
    search_fields = ('name', 'author__name', 'summary', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 25
    autocomplete_fields = ('author', 'category', 'level')

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
    list_display = ('title', 'book', 'order', 'duration')
    list_filter = ('book',)
    search_fields = ('title', 'book__name')
    ordering = ('book', 'order')

admin.site.register(MediaAsset)

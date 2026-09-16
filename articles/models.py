from django.db import models
from django.utils.text import slugify
from accounts.models import User


class ArticleCategory(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, allow_unicode=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'دسته مقاله'
        verbose_name_plural = 'دسته‌های مقالات'

    def __str__(self):
        return self.name


class ArticleLibraryItem(models.Model):
    STATUS_CHOICES = [('unread', 'خوانده‌نشده'), ('reading', 'در حال مطالعه'), ('read', 'خوانده‌شده')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='article_library')
    article = models.ForeignKey('Article', on_delete=models.CASCADE, related_name='library_items')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='unread')
    favorite = models.BooleanField(default=False)
    progress = models.PositiveSmallIntegerField(default=0)
    last_position = models.PositiveIntegerField(default=0)
    reading_seconds = models.PositiveIntegerField(default=0)
    last_read_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'article'], name='unique_article_library_item')]
        ordering = ['-updated_at']


class ArticleAnnotation(models.Model):
    KIND_CHOICES = [('highlight', 'هایلایت'), ('note', 'یادداشت')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='article_annotations')
    article = models.ForeignKey('Article', on_delete=models.CASCADE, related_name='annotations')
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default='highlight')
    selected_text = models.TextField()
    note = models.TextField(blank=True)
    color = models.CharField(max_length=20, default='amber')
    text_prefix = models.TextField(blank=True)
    text_suffix = models.TextField(blank=True)
    rects = models.JSONField(default=list, blank=True)
    page = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']


class Article(models.Model):
    ACCESS_CHOICES = [('open', 'آزاد'), ('external', 'نسخه خارجی')]
    title = models.CharField(max_length=500)
    title_fa = models.CharField(max_length=500, blank=True)
    slug = models.SlugField(max_length=550, unique=True, allow_unicode=True)
    authors = models.CharField(max_length=1000, blank=True)
    abstract = models.TextField(blank=True)
    abstract_fa = models.TextField(blank=True)
    full_text = models.TextField(blank=True)
    full_text_fa = models.TextField(blank=True)
    translation_status = models.CharField(max_length=20, default='pending', choices=[('pending','در انتظار ترجمه'),('translated','ترجمه شده'),('reviewed','بازبینی شده')])
    translation_hash = models.CharField(max_length=64, blank=True)
    translated_at = models.DateTimeField(null=True, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    journal = models.CharField(max_length=500, blank=True)
    doi = models.CharField(max_length=300, blank=True)
    source_url = models.URLField(blank=True)
    pdf_url = models.URLField(blank=True)
    pdf = models.FileField(upload_to='articles/pdfs/', blank=True)
    cover = models.ImageField(upload_to='articles/covers/', blank=True)
    category = models.ForeignKey(ArticleCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='articles')
    access = models.CharField(max_length=20, choices=ACCESS_CHOICES, default='open')
    featured = models.BooleanField(default=False)
    published = models.BooleanField(default=True)
    downloads = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-featured', '-year', '-created_at']
        verbose_name = 'مقاله'
        verbose_name_plural = 'مقالات'
        indexes = [models.Index(fields=['year']), models.Index(fields=['published']), models.Index(fields=['translation_status'])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)[:550]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title_fa or self.title

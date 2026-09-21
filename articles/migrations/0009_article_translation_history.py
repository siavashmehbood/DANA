# Generated manually for DANA 2.0 article provenance and translation history.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('articles', '0008_article_citation_count_article_external_id_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ArticleSource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=180)),
                ('base_url', models.URLField(blank=True)),
                ('feed_url', models.URLField(blank=True)),
                ('source_type', models.CharField(choices=[('rss','RSS'),('api','API'),('manual','دستی')], default='rss', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('allow_full_republish', models.BooleanField(default=False)),
                ('attribution_required', models.BooleanField(default=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name':'منبع مقاله','verbose_name_plural':'منابع مقالات','ordering':['name']},
        ),
        migrations.AddField(model_name='article', name='original_language', field=models.CharField(default='en', max_length=16)),
        migrations.AddField(model_name='article', name='publication_date', field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='article', name='retrieved_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='article', name='translation_error', field=models.TextField(blank=True)),
        migrations.AddField(model_name='article', name='translation_quality', field=models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField(model_name='article', name='translation_version', field=models.PositiveIntegerField(default=0)),
        migrations.AlterField(model_name='article', name='translation_status', field=models.CharField(choices=[('pending','در انتظار ترجمه'),('translating','در حال ترجمه'),('translated','ترجمه شده'),('reviewed','بازبینی شده'),('failed','خطای ترجمه')], default='pending', max_length=20)),
        migrations.AddField(model_name='article', name='source', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='articles', to='articles.articlesource')),
        migrations.CreateModel(
            name='ArticleTranslationVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.PositiveIntegerField()),
                ('title_fa', models.CharField(blank=True, max_length=500)),
                ('abstract_fa', models.TextField(blank=True)),
                ('content_fa', models.TextField(blank=True)),
                ('provider', models.CharField(blank=True, max_length=80)),
                ('quality_score', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('source_hash', models.CharField(blank=True, max_length=64)),
                ('is_valid', models.BooleanField(default=True)),
                ('error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='translation_versions', to='articles.article')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='article_translation_versions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering':['-version']},
        ),
        migrations.AddConstraint(model_name='articletranslationversion', constraint=models.UniqueConstraint(fields=('article','version'), name='unique_article_translation_version')),
    ]

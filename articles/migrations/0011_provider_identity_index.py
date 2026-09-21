from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('articles','0010_unique_article_source_name')]
    operations=[migrations.AddIndex(model_name='article',index=models.Index(fields=['source_provider','external_id'],name='articles_ar_source__ba3017_idx'))]

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('articles','0009_article_translation_history')]
    operations=[migrations.AddConstraint(model_name='articlesource',constraint=models.UniqueConstraint(fields=('name',),name='unique_article_source_name'))]

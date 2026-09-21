import django.core.validators
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('books','0002_unique_chapter_order')]
    operations=[migrations.AlterField(model_name='book',name='preview_percent',field=models.PositiveSmallIntegerField(default=10,validators=[django.core.validators.MaxValueValidator(100)]))]

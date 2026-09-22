from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('books', '0006_validate_media_extensions')]
    operations = [
        migrations.AlterField(
            model_name='book',
            name='slug',
            field=models.SlugField(allow_unicode=True, blank=True, max_length=250, unique=True),
        ),
    ]

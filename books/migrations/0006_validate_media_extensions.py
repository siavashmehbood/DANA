from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [('books', '0005_subscription_catalog_flag')]

    operations = [
        migrations.AlterField(
            model_name='book',
            name='pdf',
            field=models.FileField(blank=True, null=True, upload_to='books/pdf/', validators=[django.core.validators.FileExtensionValidator(['pdf'])]),
        ),
        migrations.AlterField(
            model_name='book',
            name='audio',
            field=models.FileField(blank=True, null=True, upload_to='books/audio/', validators=[django.core.validators.FileExtensionValidator(['mp3','m4a','aac','ogg','wav'])]),
        ),
        migrations.AlterField(
            model_name='chapter',
            name='audio',
            field=models.FileField(blank=True, null=True, upload_to='chapters/audio/', validators=[django.core.validators.FileExtensionValidator(['mp3','m4a','aac','ogg','wav'])]),
        ),
    ]

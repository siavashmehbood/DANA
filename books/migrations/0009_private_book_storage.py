from django.db import migrations, models
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator


private_book_storage = FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT, base_url=None)


class Migration(migrations.Migration):
    dependencies = [('books', '0008_book_featured')]

    operations = [
        migrations.AlterField(
            model_name='book',
            name='pdf',
            field=models.FileField(blank=True, null=True, storage=private_book_storage, upload_to='books/pdf/', validators=[FileExtensionValidator(['pdf'])]),
        ),
        migrations.AlterField(
            model_name='book',
            name='audio',
            field=models.FileField(blank=True, null=True, storage=private_book_storage, upload_to='books/audio/', validators=[FileExtensionValidator(['mp3', 'm4a', 'aac', 'ogg', 'wav'])]),
        ),
        migrations.AlterField(
            model_name='chapter',
            name='audio',
            field=models.FileField(blank=True, null=True, storage=private_book_storage, upload_to='chapters/audio/', validators=[FileExtensionValidator(['mp3', 'm4a', 'aac', 'ogg', 'wav'])]),
        ),
    ]

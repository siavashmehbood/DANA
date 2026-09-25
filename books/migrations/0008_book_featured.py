from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies=[('books','0007_book_slug_generation_support')]
    operations=[migrations.AddField(model_name='book',name='featured',field=models.BooleanField(default=False,verbose_name='پیشنهاد ویژه'))]

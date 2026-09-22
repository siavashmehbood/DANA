from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('books', '0004_validate_prices')]

    operations = [
        migrations.AddField(
            model_name='book',
            name='subscription_included',
            field=models.BooleanField(default=False, verbose_name='subscription included'),
        ),
    ]

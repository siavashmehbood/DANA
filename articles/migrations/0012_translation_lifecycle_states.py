from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('articles', '0011_provider_identity_index')]
    operations = [
        migrations.AlterField(
            model_name='article',
            name='translation_status',
            field=models.CharField(
                max_length=20,
                default='pending',
                choices=[
                    ('not_requested','درخواست نشده'), ('pending','در انتظار ترجمه'),
                    ('translating','در حال ترجمه'), ('translated','ترجمه شده'),
                    ('reviewed','بازبینی شده'), ('validation_failed','رد شده در کنترل کیفیت'),
                    ('provider_failed','خطای ارائه‌دهنده'), ('retry_pending','در انتظار تلاش مجدد'),
                    ('original_only','فقط متن اصلی'), ('failed','خطای ترجمه'),
                ],
            ),
        ),
    ]

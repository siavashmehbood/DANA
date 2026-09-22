from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('reader','0003_unique_review')]
    operations=[
        migrations.AddConstraint(
            model_name='bookmark',
            constraint=models.UniqueConstraint(fields=('user','book','page'),name='unique_bookmark_page'),
        ),
    ]

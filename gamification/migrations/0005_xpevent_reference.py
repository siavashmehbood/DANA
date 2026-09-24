from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('gamification', '0004_unique_point_reference')]
    operations = [
        migrations.AddField(
            model_name='xpevent',
            name='reference',
            field=models.CharField(blank=True, max_length=120, null=True, unique=True),
        ),
    ]

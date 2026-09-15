from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('gamification', '0002_gamification_expansion'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='userbadge',
            unique_together=set(),
        ),
    ]

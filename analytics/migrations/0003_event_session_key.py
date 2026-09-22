from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('analytics','0002_event_indexes')]
    operations=[
        migrations.AddField(
            model_name='event',
            name='session_key',
            field=models.CharField(blank=True,db_index=True,editable=False,max_length=64),
        ),
    ]

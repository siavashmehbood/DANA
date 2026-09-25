from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('notifications','0001_initial')]
    operations=[
        migrations.AddIndex(model_name='notification',index=models.Index(fields=['user','-created_at'],name='notify_user_created_idx')),
        migrations.AddIndex(model_name='notification',index=models.Index(fields=['user','read_at'],name='notify_user_read_idx')),
    ]

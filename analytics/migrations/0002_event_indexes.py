from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies=[('analytics','0001_initial')]
    operations=[
      migrations.AddIndex(model_name='event',index=models.Index(fields=['name','created_at'],name='analytics_e_name_6ca12c_idx')),
      migrations.AddIndex(model_name='event',index=models.Index(fields=['user','created_at'],name='analytics_e_user_id_9a87e5_idx')),
    ]

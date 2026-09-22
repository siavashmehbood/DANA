from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('support','0003_alter_ticket_priority_alter_ticket_status')]
    operations=[
        migrations.AddIndex(model_name='ticket',index=models.Index(fields=['user','-updated_at'],name='support_user_updated_idx')),
        migrations.AddIndex(model_name='ticket',index=models.Index(fields=['status','priority','-updated_at'],name='support_queue_idx')),
    ]

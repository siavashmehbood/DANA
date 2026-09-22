from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('shop','0007_subscription_models')]
    operations=[
        migrations.AddConstraint(
            model_name='subscription',
            constraint=models.UniqueConstraint(fields=('user',),condition=models.Q(status='active'),name='unique_active_subscription_per_user'),
        ),
    ]

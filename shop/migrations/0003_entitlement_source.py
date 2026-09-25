from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('shop', '0002_checkoutrequest_payment_and_more')]
    operations = [
        migrations.AddField(
            model_name='entitlement',
            name='source',
            field=models.CharField(choices=[('purchase','خرید'),('subscription','اشتراک'),('promotion','هدیه/کمپین'),('admin','اعطای مدیر'),('gift','هدیه')], default='purchase', max_length=20),
        ),
    ]

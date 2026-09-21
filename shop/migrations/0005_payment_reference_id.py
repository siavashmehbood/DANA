from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies=[('shop','0004_coupon_validation_entitlement_index')]
    operations=[migrations.AddField(model_name='payment',name='reference_id',field=models.CharField(blank=True,max_length=150))]

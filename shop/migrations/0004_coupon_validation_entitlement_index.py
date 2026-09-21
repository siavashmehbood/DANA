import django.core.validators
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('shop','0003_entitlement_source')]
    operations=[
        migrations.AlterField(model_name='coupon',name='percent',field=models.PositiveSmallIntegerField(default=0,validators=[django.core.validators.MaxValueValidator(100)])),
        migrations.AddIndex(model_name='entitlement',index=models.Index(fields=['user','expires_at'],name='shop_entitl_user_id_exp_idx')),
    ]

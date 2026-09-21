import django.core.validators
from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies=[('shop','0005_payment_reference_id')]
    operations=[
      migrations.AlterField(model_name='coupon',name='amount',field=models.DecimalField(decimal_places=0,default=0,max_digits=14,validators=[django.core.validators.MinValueValidator(0)])),
      migrations.AlterField(model_name='coupon',name='min_order',field=models.DecimalField(decimal_places=0,default=0,max_digits=14,validators=[django.core.validators.MinValueValidator(0)])),
    ]

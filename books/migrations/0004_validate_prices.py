import django.core.validators
from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies=[('books','0003_validate_preview_percent')]
    operations=[
      migrations.AlterField(model_name='book',name='old_price',field=models.DecimalField(decimal_places=0,default=0,max_digits=14,validators=[django.core.validators.MinValueValidator(0)])),
      migrations.AlterField(model_name='book',name='price',field=models.DecimalField(decimal_places=0,default=0,max_digits=14,validators=[django.core.validators.MinValueValidator(0)])),
    ]

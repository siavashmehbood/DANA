from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [('shop', '0008_subscription_unique_active_subscription_per_user')]

    operations = [
        migrations.AlterField(
            model_name='wallettransaction',
            name='amount',
            field=models.DecimalField(decimal_places=0, max_digits=14, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]

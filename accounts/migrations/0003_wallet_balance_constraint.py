from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_gamification_fields')]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='wallet_balance',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=14, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]

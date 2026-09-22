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
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(condition=models.Q(wallet_balance__gte=0), name='account_wallet_nonnegative'),
        ),
    ]

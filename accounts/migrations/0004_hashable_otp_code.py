from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0003_wallet_balance_constraint')]

    operations = [
        migrations.AlterField(
            model_name='otpcode',
            name='code',
            field=models.CharField(max_length=128),
        ),
    ]

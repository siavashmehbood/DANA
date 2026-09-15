from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='user',
            name='purchase_points',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name='user',
            name='study_points',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name='user',
            name='leaderboard_public',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='otpcode',
            name='code',
            field=models.CharField(max_length=5),
        ),
    ]

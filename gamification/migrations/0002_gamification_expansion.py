from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('gamification', '0001_initial')]
    operations = [
        migrations.CreateModel(
            name='GamificationLevel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)),
                ('min_xp', models.PositiveIntegerField(default=0)),
                ('order', models.PositiveIntegerField(default=1)),
                ('description', models.TextField(blank=True)),
                ('benefits', models.TextField(blank=True)),
                ('active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['order', 'min_xp']},
        ),
        migrations.CreateModel(
            name='Mission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=150)),
                ('description', models.TextField(blank=True)),
                ('period', models.CharField(choices=[('daily','روزانه'),('weekly','هفتگی'),('monthly','ماهانه')], max_length=20)),
                ('target', models.PositiveIntegerField(default=1)),
                ('xp_reward', models.PositiveIntegerField(default=0)),
                ('study_points_reward', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserStreak',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_days', models.PositiveIntegerField(default=0)),
                ('longest_days', models.PositiveIntegerField(default=0)),
                ('last_activity_date', models.DateField(blank=True, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='streak', to='accounts.user')),
            ],
        ),
        migrations.CreateModel(
            name='HallOfFameRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(max_length=50)),
                ('value', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('period', models.CharField(default='all', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.user')),
            ],
        ),
        migrations.CreateModel(
            name='PointLedger',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('point_type', models.CharField(choices=[('purchase','خرید'),('study','مطالعه')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('reason', models.CharField(max_length=250)),
                ('reference', models.CharField(blank=True, max_length=100)),
                ('revoked', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('book', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='books.book')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='point_ledger', to='accounts.user')),
            ],
        ),
        migrations.CreateModel(
            name='UserMission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('progress', models.PositiveIntegerField(default=0)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('period_key', models.CharField(max_length=20)),
                ('mission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gamification.mission')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.user')),
            ],
        ),
        migrations.AddField(model_name='badge', name='tier', field=models.CharField(default='bronze', max_length=20)),
        migrations.AddField(model_name='badge', name='active', field=models.BooleanField(default=True)),
        migrations.AddField(model_name='xpevent', name='source', field=models.CharField(blank=True, max_length=40)),
        migrations.AddConstraint(model_name='usermission', constraint=models.UniqueConstraint(fields=('user','mission','period_key'), name='unique_user_mission_period')),
        migrations.AddConstraint(model_name='userbadge', constraint=models.UniqueConstraint(fields=('user','badge'), name='unique_user_badge')),
    ]

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django.core.validators

class Migration(migrations.Migration):
    dependencies=[('shop','0006_validate_coupon_amounts'),('accounts','0001_initial')]
    operations=[
        migrations.CreateModel(
            name='SubscriptionPlan',
            fields=[
                ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
                ('name',models.CharField(max_length=120)),
                ('slug',models.SlugField(unique=True)),
                ('price',models.DecimalField(decimal_places=0,max_digits=14,validators=[django.core.validators.MinValueValidator(0)])),
                ('duration_days',models.PositiveIntegerField(default=30,validators=[django.core.validators.MinValueValidator(1)])),
                ('active',models.BooleanField(default=True)),
                ('description',models.TextField(blank=True)),
                ('created_at',models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
                ('status',models.CharField(choices=[('active','فعال'),('expired','منقضی'),('cancelled','لغوشده')],default='active',max_length=20)),
                ('starts_at',models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_at',models.DateTimeField()),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('plan',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='subscriptions',to='shop.subscriptionplan')),
                ('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='subscriptions',to='accounts.user')),
            ],
        ),
        migrations.AddIndex(model_name='subscription',index=models.Index(fields=['user','status','expires_at'],name='shop_sub_user_status_idx')),
        migrations.AddConstraint(model_name='subscription',constraint=models.CheckConstraint(condition=models.Q(expires_at__gt=models.F('starts_at')),name='subscription_expiry_after_start')),
    ]

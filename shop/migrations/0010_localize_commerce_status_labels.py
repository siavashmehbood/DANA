from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies=[('shop','0009_wallet_transaction_amount_validation')]
    operations=[
        migrations.AlterField(model_name='order',name='status',field=models.CharField(max_length=20,default='pending',choices=[('pending','در انتظار پرداخت'),('paid','پرداخت‌شده'),('cancelled','لغوشده'),('gift','هدیه')])),
        migrations.AlterField(model_name='payment',name='status',field=models.CharField(max_length=20,default='pending',choices=[('pending','در انتظار'),('successful','موفق'),('failed','ناموفق'),('cancelled','لغوشده'),('refunded','بازپرداخت‌شده')])),
        migrations.AlterField(model_name='wallettransaction',name='type',field=models.CharField(max_length=20,choices=[('credit','واریز'),('debit','برداشت'),('refund','بازپرداخت'),('reward','پاداش')])),
    ]

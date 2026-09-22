from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('support','0002_ticket_assigned_to_ticket_category_ticket_priority_and_more')]
    operations=[
        migrations.AlterField(model_name='ticket',name='priority',field=models.CharField(choices=[('low','کم'),('normal','عادی'),('high','زیاد'),('urgent','فوری')],default='normal',max_length=20)),
        migrations.AlterField(model_name='ticket',name='status',field=models.CharField(choices=[('open','باز'),('in_progress','در حال بررسی'),('waiting','منتظر پاسخ'),('resolved','حل‌شده'),('closed','بسته')],default='open',max_length=20)),
    ]

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('books','0001_initial')]
    operations=[
        migrations.AlterModelOptions(name='chapter',options={'ordering':['order']}),
        migrations.AddConstraint(model_name='chapter',constraint=models.UniqueConstraint(fields=('book','order'),name='unique_chapter_order_per_book')),
    ]

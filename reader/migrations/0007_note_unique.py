from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('reader','0006_highlight')]
    operations=[
        migrations.AlterModelOptions(name='note',options={}),
        migrations.AddConstraint(model_name='note',constraint=models.UniqueConstraint(fields=('user','book','page','text'),name='unique_reader_note')),
    ]

from django.db import migrations, models
import django.core.validators
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[('reader','0010_reading_activity')]
    operations=[
        migrations.CreateModel(
            name='ListeningActivity',
            fields=[
                ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
                ('seconds',models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('book',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to='books.book')),
                ('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to='accounts.user')),
            ],
        ),
        migrations.AddIndex(model_name='listeningactivity',index=models.Index(fields=['user','-created_at'],name='reader_listen_recent_idx')),
    ]

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[('reader','0008_readinggoal')]
    operations=[
        migrations.CreateModel(
            name='AudioProgress',
            fields=[
                ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
                ('position_seconds',models.PositiveIntegerField(default=0)),
                ('duration_seconds',models.PositiveIntegerField(default=0)),
                ('completed',models.BooleanField(default=False)),
                ('updated_at',models.DateTimeField(auto_now=True)),
                ('book',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to='books.book')),
                ('chapter',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.CASCADE,to='books.chapter')),
                ('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to='accounts.user')),
            ],
        ),
        migrations.AddConstraint(model_name='audioprogress',constraint=models.UniqueConstraint(fields=('user','book','chapter'),name='unique_audio_progress_chapter')),
        migrations.AddIndex(model_name='audioprogress',index=models.Index(fields=['user','book','-updated_at'],name='reader_audio_recent_idx')),
    ]

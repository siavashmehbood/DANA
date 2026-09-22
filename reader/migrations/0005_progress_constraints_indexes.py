from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('reader','0004_unique_bookmark_page')]
    operations=[
        migrations.AlterUniqueTogether(name='readingprogress',unique_together=set()),
        migrations.AddConstraint(model_name='readingprogress',constraint=models.UniqueConstraint(fields=('user','book'),name='unique_reading_progress')),
        migrations.AddIndex(model_name='readingprogress',index=models.Index(fields=['user','-updated_at'],name='reader_progress_recent_idx')),
    ]

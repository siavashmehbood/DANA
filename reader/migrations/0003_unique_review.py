from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('reader','0002_savedword')]
    operations=[migrations.AddConstraint(model_name='review',constraint=models.UniqueConstraint(fields=('user','book'),name='unique_review_per_user_book'))]

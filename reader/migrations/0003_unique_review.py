import django.core.validators
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('reader','0002_savedword')]
    operations=[migrations.AlterField(model_name='review',name='rating',field=models.PositiveSmallIntegerField(default=5,validators=[django.core.validators.MinValueValidator(1),django.core.validators.MaxValueValidator(5)])),migrations.AlterField(model_name='review',name='admin_score',field=models.PositiveSmallIntegerField(blank=True,null=True,validators=[django.core.validators.MinValueValidator(1),django.core.validators.MaxValueValidator(10)])),migrations.AddConstraint(model_name='review',constraint=models.UniqueConstraint(fields=('user','book'),name='unique_review_per_user_book'))]

from django.db import migrations, models
import django.core.validators
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[('accounts','0001_initial'),('reader','0007_note_unique')]
    operations=[
        migrations.CreateModel(
            name='ReadingGoal',
            fields=[
                ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
                ('weekly_minutes',models.PositiveIntegerField(default=120,validators=[django.core.validators.MinValueValidator(1),django.core.validators.MaxValueValidator(10080)])),
                ('weekly_books',models.PositiveSmallIntegerField(default=1,validators=[django.core.validators.MinValueValidator(1),django.core.validators.MaxValueValidator(100)])),
                ('updated_at',models.DateTimeField(auto_now=True)),
                ('user',models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,related_name='reading_goal',to='accounts.user')),
            ],
        ),
    ]

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[('accounts','0001_initial'),('books','0004_validate_prices'),('reader','0005_progress_constraints_indexes')]
    operations=[
        migrations.CreateModel(
            name='Highlight',
            fields=[
                ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
                ('page',models.PositiveIntegerField()),
                ('text',models.TextField()),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('book',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to='books.book')),
                ('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to='accounts.user')),
            ],
        ),
        migrations.AddIndex(model_name='highlight',index=models.Index(fields=['user','book','page'],name='reader_highlight_lookup_idx')),
    ]

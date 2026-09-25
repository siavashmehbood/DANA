from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('gamification','0003_alter_userbadge_unique_together')]
    operations=[
        migrations.RunSQL(
            "UPDATE gamification_pointledger SET reference = NULL WHERE reference = '';",
            reverse_sql="UPDATE gamification_pointledger SET reference = '' WHERE reference IS NULL;",
        ),
        migrations.AlterField(
            model_name='pointledger',
            name='reference',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
    ]

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("articles", "0013_article_identity_constraints"),
        ("articles", "0013_seed_public_article_fallback"),
    ]
    operations = []

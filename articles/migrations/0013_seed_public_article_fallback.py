from django.db import migrations


class Migration(migrations.Migration):
    """
    Historical marker for a migration that was applied in production and later
    removed.  The original migration seeded temporary fallback article data.
    Restoring the migration name as a no-op keeps Django's migration history
    consistent without recreating that test-only content on fresh databases.
    """

    dependencies = [("articles", "0012_translation_lifecycle_states")]
    operations = []

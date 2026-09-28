from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = "Report applied migration records that no longer exist on disk."

    def handle(self, *args, **options):
        loader = MigrationLoader(connection, ignore_no_migrations=True)
        disk = set(loader.disk_migrations)
        applied = set(MigrationRecorder(connection).applied_migrations())
        orphans = sorted(applied - disk)

        for app_label, migration_name in orphans:
            self.stdout.write(f"ORPHAN {app_label}.{migration_name}")
        self.stdout.write(f"ORPHAN_COUNT={len(orphans)}")

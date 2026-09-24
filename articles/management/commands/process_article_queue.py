from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from articles.models import Article
from articles.services import _process_article


class Command(BaseCommand):
    help = 'پردازش پایدار صف مقالات بدون وابستگی به thread فرایند وب'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=25)

    def handle(self, *args, **options):
        limit=max(1, options['limit'])
        processed=0
        stale_before=timezone.now()-timezone.timedelta(minutes=15)
        while processed < limit:
            with transaction.atomic():
                row=(Article.objects.select_for_update(skip_locked=True)
                     .filter(published=True)
                     .filter(Q(translation_status__in=['pending','retry_pending']) | Q(translation_status='translating',updated_at__lt=stale_before))
                     .order_by('pk').first())
                if not row:
                    break
                Article.objects.filter(pk=row.pk).update(translation_status='translating', updated_at=timezone.now())
                article_id=row.pk
            _process_article(article_id)
            processed += 1
        self.stdout.write(self.style.SUCCESS(f'{processed} مقاله از صف پردازش شد.'))

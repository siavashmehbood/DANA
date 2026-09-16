from django.core.management.base import BaseCommand, CommandError
from articles.importer import import_discovered
from articles.models import ArticleCategory


class Command(BaseCommand):
    help = 'Discover and import recent/high-value academic articles from multiple providers.'

    def add_arguments(self, parser):
        parser.add_argument('query', nargs='?', default='latest research')
        parser.add_argument('--limit', type=int, default=30)
        parser.add_argument('--category', default='')
        parser.add_argument('--providers', default='openalex,semantic_scholar,crossref')

    def handle(self, *args, **options):
        if not 1 <= options['limit'] <= 100:
            raise CommandError('limit must be between 1 and 100')
        category = None
        if options['category']:
            category, _ = ArticleCategory.objects.get_or_create(
                slug=options['category'], defaults={'name': options['category']}
            )
        providers = [p.strip() for p in options['providers'].split(',') if p.strip()]
        result = import_discovered(options['query'], options['limit'], category, providers)
        self.stdout.write(self.style.SUCCESS(
            f"Discovered: {result['discovered']} | New: {result['created']} | Updated: {result['updated']}"
        ))

# Example Windows Task Scheduler command:
# .venv\Scripts\python.exe manage.py auto_discover_articles "artificial intelligence" --limit 20
# Run once per day for each DANA topic. The importer is idempotent by DOI/external id/title.

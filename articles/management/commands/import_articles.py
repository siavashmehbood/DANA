from django.core.management.base import BaseCommand, CommandError
from articles.importer import import_openalex
from articles.models import ArticleCategory


class Command(BaseCommand):
    help = 'Import academic articles from OpenAlex'

    def add_arguments(self, parser):
        parser.add_argument('query')
        parser.add_argument('--limit', type=int, default=20)
        parser.add_argument('--category', default='')

    def handle(self, *args, **options):
        category = None
        if options['category']:
            category, _ = ArticleCategory.objects.get_or_create(
                slug=options['category'], defaults={'name': options['category']}
            )
        if options['limit'] < 1 or options['limit'] > 200:
            raise CommandError('limit must be between 1 and 200')
        result = import_openalex(options['query'], options['limit'], category)
        self.stdout.write(self.style.SUCCESS(
            f"Imported: {result['created']} new, {result['updated']} updated"
        ))

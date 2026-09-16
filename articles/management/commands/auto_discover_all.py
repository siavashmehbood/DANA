from django.core.management.base import BaseCommand
from articles.importer import import_discovered


DEFAULT_TOPICS = [
    'artificial intelligence machine learning',
    'computer science software engineering',
    'data science cybersecurity',
    'psychology neuroscience cognitive science',
    'medicine biomedical research',
    'economics business management',
    'physics astronomy',
]


class Command(BaseCommand):
    help = 'Discover new academic articles across DANA research topics.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=12)
        parser.add_argument('--topic', action='append', dest='topics')

    def handle(self, *args, **options):
        topics = options.get('topics') or DEFAULT_TOPICS
        total_new = total_updated = total_found = 0
        for topic in topics:
            result = import_discovered(topic, options['limit'])
            total_found += result['discovered']
            total_new += result['created']
            total_updated += result['updated']
            self.stdout.write(f"{topic}: found={result['discovered']} new={result['created']} updated={result['updated']}")
        self.stdout.write(self.style.SUCCESS(
            f'TOTAL found={total_found} new={total_new} updated={total_updated}'
        ))

# Recommended scheduler: run this command daily after traffic is low.






# End of command.

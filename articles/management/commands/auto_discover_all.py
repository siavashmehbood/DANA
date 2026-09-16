from django.core.management.base import BaseCommand
from articles.importer import import_discovered
from articles.models import ArticleCategory


TOPIC_CATALOG = [
    ('هوش مصنوعی و یادگیری ماشین', 'artificial intelligence machine learning'),
    ('علوم کامپیوتر و نرم‌افزار', 'computer science software engineering'),
    ('داده و امنیت سایبری', 'data science cybersecurity'),
    ('زبان و زبان‌شناسی', 'linguistics language linguistics'),
    ('ادبیات و مطالعات ادبی', 'literature literary studies'),
    ('سینما و فیلم', 'film cinema movie studies film studies'),
    ('هنر و رسانه', 'arts media communication'),
    ('تاریخ و باستان‌شناسی', 'history archaeology'),
    ('فلسفه و اخلاق', 'philosophy ethics'),
    ('روان‌شناسی و علوم شناختی', 'psychology neuroscience cognitive science'),
    ('علوم اجتماعی و جامعه‌شناسی', 'social sciences sociology anthropology'),
    ('اقتصاد و کسب‌وکار', 'economics business management'),
    ('حقوق و مطالعات حقوقی', 'law legal studies'),
    ('آموزش و یادگیری', 'education learning pedagogy'),
    ('پزشکی و سلامت', 'medicine health biomedical research'),
    ('زیست‌شناسی و ژنتیک', 'biology genetics molecular biology'),
    ('محیط زیست و اقلیم', 'environment climate ecology'),
    ('نجوم و اخترفیزیک', 'astronomy astrophysics space science'),
    ('فیزیک', 'physics quantum physics particle physics'),
    ('شیمی', 'chemistry materials chemistry'),
    ('ریاضیات و آمار', 'mathematics statistics'),
    ('زمین‌شناسی و علوم زمین', 'geology geoscience earth science'),
    ('مهندسی', 'engineering mechanical electrical civil engineering'),
    ('کشاورزی و علوم غذایی', 'agriculture food science agricultural biology'),
]


class Command(BaseCommand):
    help = 'Discover and import academic articles across DANA subject categories.'

    def _write_safe(self, message, style=None):
        """Keep management commands usable on legacy Windows code pages."""
        output = self.style.SUCCESS(message) if style == 'success' else message
        try:
            self.stdout.write(output)
        except UnicodeEncodeError:
            fallback = message.encode('ascii', 'backslashreplace').decode('ascii')
            self.stdout.write(fallback)

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=12)
        parser.add_argument('--topic', action='append', dest='topics')
        parser.add_argument('--only', nargs='+', help='Run selected category slugs/names only.')

    def handle(self, *args, **options):
        selected = options.get('topics')
        catalog = TOPIC_CATALOG
        if selected:
            wanted = {str(x).strip().lower() for x in selected}
            catalog = [
                (name, query) for name, query in catalog
                if name.lower() in wanted or query.lower() in wanted
                or query.replace(' ', '-').lower() in wanted
            ]
        total_new = total_updated = total_found = 0
        for name, query in catalog:
            category, _ = ArticleCategory.objects.get_or_create(
                slug=query.replace(' ', '-'), defaults={'name': name}
            )
            if category.name != name:
                category.name = name
                category.save(update_fields=['name'])
            result = import_discovered(query, options['limit'], category)
            total_found += result['discovered']
            total_new += result['created']
            total_updated += result['updated']
            self._write_safe(
                f"{name}: found={result['discovered']} new={result['created']} "
                f"updated={result['updated']}"
            )
        self._write_safe(
            f'TOTAL found={total_found} new={total_new} updated={total_updated} '
            f'categories={len(catalog)}',
            style='success',
        )

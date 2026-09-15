from django.core.management.base import BaseCommand
from articles.downloader import download_pdf
from articles.models import Article


class Command(BaseCommand):
    help = 'Download available Open Access article PDFs'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=20)

    def handle(self, *args, **options):
        articles = Article.objects.exclude(pdf_url='').filter(pdf='')[:options['limit']]
        done = failed = 0
        for article in articles:
            try:
                if download_pdf(article):
                    done += 1
                else:
                    failed += 1
            except Exception as exc:
                failed += 1
                self.stdout.write(f'Failed: {article.title[:60]} | {exc}')
        self.stdout.write(self.style.SUCCESS(f'Downloaded: {done} | Skipped/failed: {failed}'))

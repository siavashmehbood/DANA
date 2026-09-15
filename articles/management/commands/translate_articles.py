from django.core.management.base import BaseCommand

from articles.models import Article
from articles.translation import download_article_pdf, translate_article


class Command(BaseCommand):
    help = 'ترجمه دسته‌ای همه مقاله‌های منتشرشده'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument('--all', action='store_true')
        parser.add_argument('--full', action='store_true')
        parser.add_argument('--download', action='store_true')
        parser.add_argument('--force', action='store_true')

    def handle(self, *args, **options):
        articles = Article.objects.filter(published=True).order_by('pk')
        if not options['all']:
            articles = articles.filter(translation_status='pending')
        if options['limit']:
            articles = articles[:options['limit']]
        total = articles.count()
        if not total:
            self.stdout.write(self.style.SUCCESS('مقاله‌ای برای ترجمه وجود ندارد.'))
            return

        done = failed = downloaded = 0
        for index, article in enumerate(articles.iterator(), 1):
            try:
                if options['download'] and article.pdf_url and not article.pdf:
                    if download_article_pdf(article):
                        downloaded += 1
                translate_article(article, full_text=options['full'], force=options['force'])
                done += 1
                self.stdout.write(f'[{index}/{total}] OK | {article.title[:80]}')
            except Exception as exc:
                failed += 1
                self.stderr.write(f'[{index}/{total}] FAIL | {article.title[:80]} | {exc}')

        self.stdout.write(self.style.SUCCESS(
            f'تمام شد: {done} موفق، {failed} ناموفق، {downloaded} PDF دریافت شد.'
        ))

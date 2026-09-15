from django.core.management.base import BaseCommand

from articles.models import Article
from articles.translation import extract_pdf_text


class Command(BaseCommand):
    help = 'Extract PDF text into the internal article reader.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument('--force', action='store_true')

    def handle(self, *args, **options):
        qs = Article.objects.filter(published=True).exclude(pdf='').order_by('pk')
        if not options['force']:
            qs = qs.filter(full_text='')
        if options['limit']:
            qs = qs[:options['limit']]

        total = qs.count()
        success = 0
        failed = 0
        for index, article in enumerate(qs.iterator(), 1):
            try:
                text = extract_pdf_text(article)
                if not text:
                    self.stdout.write(f'[{index}/{total}] EMPTY  {article.title}')
                    continue
                article.full_text = text
                article.save(update_fields=['full_text', 'updated_at'])
                success += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[{index}/{total}] OK  {article.title} -> {len(text):,} chars'
                    )
                )
            except Exception as exc:
                failed += 1
                self.stderr.write(f'[{index}/{total}] ERROR  {article.title}: {exc}')

        self.stdout.write(f'Finished: {success} extracted, {failed} failed.')

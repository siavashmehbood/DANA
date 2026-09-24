import logging
from django.conf import settings

from .models import Article
from .translation import download_article_pdf, extract_pdf_text, translate_article

logger = logging.getLogger(__name__)


def _process_article(article_id):
    try:
        article = Article.objects.get(pk=article_id)
        if not article.published:
            return
        if article.source_id and not article.source.is_active:
            return
        if article.source_id and not article.source.allow_full_republish:
            result=translate_article(article, full_text=False)
            if result.translation_status in {'failed','provider_failed','validation_failed'}:
                logger.warning('Automatic translation failed for article %s: %s', article_id, result.translation_error)
            return
        if not article.pdf and article.pdf_url:
            try:
                download_article_pdf(article)
            except Exception as exc:
                logger.info('PDF unavailable for article %s: %s', article_id, exc)
        if article.pdf and not article.full_text:
            try:
                text = extract_pdf_text(article)
                if text:
                    article.full_text = text
                    article.save(update_fields=['full_text', 'updated_at'])
            except Exception as exc:
                logger.info('PDF extraction failed for article %s: %s', article_id, exc)
        article.refresh_from_db(fields=['full_text'])
        result=translate_article(article, full_text=bool(article.full_text))
        if result.translation_status in {'failed','provider_failed','validation_failed'}:
            logger.warning('Automatic translation failed for article %s: %s', article_id, result.translation_error)
    except Article.DoesNotExist:
        return
    except Exception:
        logger.exception('Automatic article processing failed for %s', article_id)


def schedule_article_processing(article_id):
    """Durably mark an article for the database-backed worker.

    Web requests never own background threads; process_article_queue consumes
    these rows safely and can be supervised by the deployment environment.
    """
    article=Article.objects.filter(pk=article_id,published=True).first()
    if not article:
        return False
    if article.translation_status in {'translated','reviewed'} and article.translation_hash:
        return False
    if article.translation_status != 'pending':
        Article.objects.filter(pk=article_id).update(translation_status='pending',translation_error='')
    return True

import logging
import threading

from django.db import close_old_connections

from .models import Article
from .translation import download_article_pdf, extract_pdf_text, translate_article

logger = logging.getLogger(__name__)
_processing = set()
_processing_lock = threading.Lock()


def _process_article(article_id):
    try:
        article = Article.objects.get(pk=article_id)
        if not article.published:
            return
        if article.source_id and not article.source.is_active:
            return
        if article.source_id and not article.source.allow_full_republish:
            result=translate_article(article, full_text=False)
            if result.translation_status == 'failed':
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
        if result.translation_status == 'failed':
            logger.warning('Automatic translation failed for article %s: %s', article_id, result.translation_error)
    except Article.DoesNotExist:
        return
    except Exception:
        logger.exception('Automatic article processing failed for %s', article_id)
    finally:
        with _processing_lock:
            _processing.discard(article_id)


def _article_worker(article_id):
    # Connection lifecycle belongs to the background-thread boundary, not the
    # processing primitive itself. Keeping it here prevents direct/synchronous
    # callers (including PostgreSQL regression tests and future workers) from
    # unexpectedly closing their active Django connection.
    close_old_connections()
    try:
        _process_article(article_id)
    finally:
        close_old_connections()


def schedule_article_processing(article_id):
    with _processing_lock:
        if article_id in _processing:
            return False
        _processing.add(article_id)
    worker = threading.Thread(
        target=_article_worker,
        args=(article_id,),
        name=f'article-processing-{article_id}',
        daemon=True,
    )
    worker.start()
    return True

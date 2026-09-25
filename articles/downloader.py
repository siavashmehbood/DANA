"""Compatibility wrapper for the hardened article PDF downloader.

Keep a single network download implementation so management commands cannot bypass
SSRF checks, redirect validation, size limits, or PDF signature validation.
"""
from .models import Article
from .translation import download_article_pdf


def download_pdf(article, timeout=45):
    if article.source_id and (not article.source.is_active or not article.source.allow_full_republish):
        return False
    # timeout is retained for backwards compatibility; the hardened downloader
    # owns its bounded network timeout and maximum response size.
    return download_article_pdf(article, max_bytes=20 * 1024 * 1024)


def download_open_pdfs(limit=20):
    count = 0
    for article in Article.objects.filter(pdf='').exclude(pdf_url='').select_related('source')[:limit]:
        if download_pdf(article):
            count += 1
    return count

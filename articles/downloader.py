from pathlib import Path
import requests
from django.core.files import File
from .models import Article


def download_pdf(article, timeout=45):
    if article.pdf or not article.pdf_url:
        return False
    response = requests.get(article.pdf_url, timeout=timeout, stream=True,
                            headers={'User-Agent': 'DANA Academic Library/1.0'})
    response.raise_for_status()
    content_type = (response.headers.get('Content-Type') or '').lower()
    if 'pdf' not in content_type and not article.pdf_url.lower().split('?')[0].endswith('.pdf'):
        return False
    filename = f'article-{article.pk}.pdf'
    temp = Path(article.pdf.storage.location) / 'articles' / 'tmp' / filename
    temp.parent.mkdir(parents=True, exist_ok=True)
    with temp.open('wb') as handle:
        for chunk in response.iter_content(chunk_size=1024 * 256):
            if chunk:
                handle.write(chunk)
    with temp.open('rb') as handle:
        article.pdf.save(filename, File(handle), save=True)
    temp.unlink(missing_ok=True)
    article.access = 'open'
    article.save(update_fields=['access', 'updated_at'])
    return True


def download_open_pdfs(limit=20):
    count = 0
    for article in Article.objects.filter(pdf__isnull=False).exclude(pdf_url='')[:limit]:
        if download_pdf(article):
            count += 1
    return count

import hashlib
import re
import time

import pymupdf
import requests
from django.core.files.base import ContentFile
from django.utils import timezone

from .models import Article

MYMEMORY_URL = 'https://api.mymemory.translated.net/get'

ROUGH_TERMS = {
    'natural language processing': 'پردازش زبان طبیعی',
    'neural network': 'شبکه عصبی',
    'deep learning': 'یادگیری عمیق',
    'machine learning': 'یادگیری ماشین',
    'large language model': 'مدل زبانی بزرگ',
    'artificial intelligence': 'هوش مصنوعی',
    'review article': 'مقاله مروری',
    'state-of-the-art': 'پیشرفته‌ترین روش‌های موجود',
    'attention mechanism': 'سازوکار توجه',
    'knowledge base': 'پایگاه دانش',
    'data set': 'مجموعه داده',
    'dataset': 'مجموعه‌داده',
    'classification': 'دسته‌بندی',
    'prediction': 'پیش‌بینی',
    'translation': 'ترجمه',
    'methods': 'روش‌ها',
    'method': 'روش',
    'models': 'مدل‌ها',
    'model': 'مدل',
    'research': 'پژوهش',
    'results': 'نتایج',
    'approach': 'رویکرد',
    'systems': 'سامانه‌ها',
    'system': 'سامانه',
    'algorithm': 'الگوریتم',
    'algorithms': 'الگوریتم‌ها',
    'languages': 'زبان‌ها',
    'language': 'زبان',
    'texts': 'متن‌ها',
    'text': 'متن',
    'training': 'آموزش',
    'trained': 'آموزش‌دیده',
    'performance': 'عملکرد',
    'information': 'اطلاعات',
    'based': 'مبتنی بر',
    'using': 'با استفاده از',
    'study': 'مطالعه',
    'analysis': 'تحلیل',
    'introduction': 'مقدمه',
    'comparative': 'مقایسه‌ای',
    'recent': 'جدیدترین',
    'advances': 'پیشرفت‌ها',
    'proposed': 'پیشنهادی',
    'we present': 'ارائه می‌کنیم',
    'this paper': 'این مقاله',
    'in this study': 'در این مطالعه',
}


def download_article_pdf(article, max_bytes=20 * 1024 * 1024):
    """Download an OpenAlex PDF when an article has no local copy."""
    if article.pdf or not article.pdf_url:
        return False
    response = requests.get(
        article.pdf_url,
        timeout=20,
        headers={'User-Agent': 'DANA/1.0'},
        stream=True,
    )
    response.raise_for_status()
    content = bytearray()
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        content.extend(chunk)
        if len(content) > max_bytes:
            raise ValueError('PDF is larger than the allowed limit')
    if not content.startswith(b'%PDF'):
        raise ValueError('Downloaded resource is not a PDF')
    filename = f'article-{article.pk}.pdf'
    article.pdf.save(filename, ContentFile(bytes(content)), save=True)
    return True


def extract_pdf_text(article):
    if not article.pdf:
        return ''
    with article.pdf.open('rb') as handle:
        data = handle.read()
    doc = pymupdf.open(stream=data, filetype='pdf')
    parts = []
    for index, page in enumerate(doc, 1):
        text = page.get_text('text').strip()
        if text:
            parts.append(f'--- Page {index} ---\n{text}')
    doc.close()
    return '\n\n'.join(parts)


def _chunks(text, limit=450):
    """Split text into API-safe chunks without losing paragraph order."""
    chunks = []
    current = ''
    for paragraph in (part.strip() for part in (text or '').split('\n')):
        if not paragraph:
            continue
        for word in paragraph.split():
            if len(word) > limit:
                if current:
                    chunks.append(current)
                    current = ''
                chunks.extend(word[index:index + limit] for index in range(0, len(word), limit))
                continue
            candidate = f'{current} {word}'.strip()
            if current and len(candidate) > limit:
                chunks.append(current)
                current = word
            else:
                current = candidate
        if current:
            chunks.append(current)
            current = ''
    return chunks


def rough_translate(text):
    """Fallback translation that keeps unknown technical words intact."""
    value = (text or '').strip()
    if not value:
        return ''
    for source, target in sorted(ROUGH_TERMS.items(), key=lambda item: -len(item[0])):
        value = re.sub(rf'\b{re.escape(source)}\b', target, value, flags=re.IGNORECASE)
    return value


def translate_text(text, delay=0.1, retries=1):
    result = []
    for chunk in _chunks(text):
        translated_chunk = ''
        for attempt in range(retries):
            try:
                response = requests.get(
                    MYMEMORY_URL,
                    params={'q': chunk, 'langpair': 'en|fa'},
                    timeout=8,
                    headers={'User-Agent': 'DANA/1.0'},
                )
                response.raise_for_status()
                translated_chunk = response.json().get('responseData', {}).get(
                    'translatedText', ''
                ).strip()
                if translated_chunk:
                    break
            except (requests.RequestException, ValueError):
                if attempt + 1 < retries:
                    time.sleep(1)
        result.append(translated_chunk or rough_translate(chunk))
        time.sleep(delay)
    return '\n\n'.join(result)


def translate_article(article, full_text=False, force=False):
    changed = []
    if force or not article.title_fa:
        article.title_fa = translate_text(article.title)
        changed.append('title_fa')
    if force or (article.abstract and not article.abstract_fa):
        article.abstract_fa = translate_text(article.abstract)
        changed.append('abstract_fa')
    if full_text and (article.pdf or article.full_text) and (force or not article.full_text_fa):
        source = article.full_text or extract_pdf_text(article)
        if source:
            article.full_text = source
            article.full_text_fa = translate_text(source)
            changed += ['full_text', 'full_text_fa']
    if changed:
        article.translation_status = 'translated'
        article.translation_hash = hashlib.sha256(
            f'{article.title}\n{article.abstract}\n{article.full_text}'.encode('utf-8')
        ).hexdigest()
        article.translated_at = timezone.now()
        article.save(update_fields=changed + [
            'translation_status', 'translation_hash', 'translated_at', 'updated_at'
        ])
    return article

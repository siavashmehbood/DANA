import hashlib
import re
import time

import pymupdf
import requests
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from .models import ArticleTranslationVersion

MYMEMORY_URL = 'https://api.mymemory.translated.net/get'

ROUGH_TERMS = {
    'natural language processing': 'پردازش زبان طبیعی', 'neural network': 'شبکه عصبی',
    'deep learning': 'یادگیری عمیق', 'machine learning': 'یادگیری ماشین',
    'large language model': 'مدل زبانی بزرگ', 'artificial intelligence': 'هوش مصنوعی',
    'review article': 'مقاله مروری', 'state-of-the-art': 'پیشرفته‌ترین روش‌های موجود',
    'attention mechanism': 'سازوکار توجه', 'knowledge base': 'پایگاه دانش',
    'data set': 'مجموعه داده', 'dataset': 'مجموعه‌داده', 'classification': 'دسته‌بندی',
    'prediction': 'پیش‌بینی', 'translation': 'ترجمه', 'methods': 'روش‌ها',
    'method': 'روش', 'models': 'مدل‌ها', 'model': 'مدل', 'research': 'پژوهش',
    'results': 'نتایج', 'approach': 'رویکرد', 'systems': 'سامانه‌ها', 'system': 'سامانه',
    'algorithm': 'الگوریتم', 'algorithms': 'الگوریتم‌ها', 'languages': 'زبان‌ها',
    'language': 'زبان', 'texts': 'متن‌ها', 'text': 'متن', 'training': 'آموزش',
    'trained': 'آموزش‌دیده', 'performance': 'عملکرد', 'information': 'اطلاعات',
    'based': 'مبتنی بر', 'using': 'با استفاده از', 'study': 'مطالعه',
    'analysis': 'تحلیل', 'introduction': 'مقدمه', 'comparative': 'مقایسه‌ای',
    'recent': 'جدیدترین', 'advances': 'پیشرفت‌ها', 'proposed': 'پیشنهادی',
    'we present': 'ارائه می‌کنیم', 'this paper': 'این مقاله', 'in this study': 'در این مطالعه',
}


def download_article_pdf(article, max_bytes=20 * 1024 * 1024):
    if article.pdf or not article.pdf_url:
        return False
    response = requests.get(article.pdf_url, timeout=20, headers={'User-Agent': 'DANA/2.0'}, stream=True)
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
    article.pdf.save(f'article-{article.pk}.pdf', ContentFile(bytes(content)), save=True)
    return True


def extract_pdf_text(article):
    if not article.pdf:
        return ''
    with article.pdf.open('rb') as handle:
        data = handle.read()
    doc = pymupdf.open(stream=data, filetype='pdf')
    pages = []

    def clean_block(raw):
        lines = [re.sub(r'\s+', ' ', line).strip() for line in raw.splitlines()]
        lines = [line for line in lines if line]
        if not lines:
            return ''
        return re.sub(r'(?<=\w)- (?=\w)', '-', ' '.join(lines)).strip()

    def merge_column(items):
        merged = []
        for text in items:
            if not merged:
                merged.append(text)
                continue
            prev = merged[-1]
            if prev.endswith('-') and text and text[0].isalnum():
                merged[-1] = prev[:-1] + text
            elif not re.search(r'[.!?:;]$', prev) and text and text[0].islower():
                merged[-1] = prev + ' ' + text
            else:
                merged.append(text)
        return merged

    for page in doc:
        blocks = []
        for block in page.get_text('blocks'):
            x0, y0, x1, y1, raw = block[:5]
            text = clean_block(raw)
            if not text or (len(text) <= 4 and text.isdigit()) or y1 < 80 or y0 > page.rect.height - 35:
                continue
            blocks.append((x0, y0, x1, y1, text))
        if not blocks:
            continue
        mid = page.rect.width / 2
        body = [b for b in blocks if b[1] >= page.rect.height * 0.35]
        left, right = [b for b in body if b[0] < mid], [b for b in body if b[0] >= mid]
        if left and right:
            top = sorted([b for b in blocks if b[1] < page.rect.height * 0.35], key=lambda b: (b[1], b[0]))
            parts = [b[4] for b in top]
            parts += merge_column([b[4] for b in sorted(left, key=lambda b: (b[1], b[0]))])
            parts += merge_column([b[4] for b in sorted(right, key=lambda b: (b[1], b[0]))])
        else:
            parts = merge_column([b[4] for b in sorted(blocks, key=lambda b: (b[1], b[0]))])
        pages.append('\n\n'.join(parts))
    doc.close()
    return '\n\n'.join(pages)


def _chunks(text, limit=450):
    chunks, current = [], ''
    for paragraph in (part.strip() for part in (text or '').split('\n')):
        if not paragraph:
            continue
        for word in paragraph.split():
            if len(word) > limit:
                if current:
                    chunks.append(current); current = ''
                chunks.extend(word[i:i + limit] for i in range(0, len(word), limit))
                continue
            candidate = f'{current} {word}'.strip()
            if current and len(candidate) > limit:
                chunks.append(current); current = word
            else:
                current = candidate
        if current:
            chunks.append(current); current = ''
    return chunks


def rough_translate(text):
    value = (text or '').strip()
    if not value:
        return ''
    for source, target in sorted(ROUGH_TERMS.items(), key=lambda item: -len(item[0])):
        value = re.sub(rf'\b{re.escape(source)}\b', target, value, flags=re.IGNORECASE)
    return value


def translate_text(text, delay=0.1, retries=1):
    result, service_exhausted = [], False
    for chunk in _chunks(text):
        translated_chunk = ''
        if not service_exhausted:
            for attempt in range(retries):
                try:
                    response = requests.get(MYMEMORY_URL, params={'q': chunk, 'langpair': 'en|fa'}, timeout=8, headers={'User-Agent': 'DANA/2.0'})
                    if response.status_code == 429:
                        service_exhausted = True
                        break
                    response.raise_for_status()
                    translated_chunk = response.json().get('responseData', {}).get('translatedText', '').strip()
                    if translated_chunk:
                        break
                except (requests.RequestException, ValueError):
                    if attempt + 1 < retries:
                        time.sleep(1)
        result.append(translated_chunk or rough_translate(chunk))
        time.sleep(delay)
    return '\n\n'.join(result)


@transaction.atomic
def translate_article(article, full_text=False, force=False, provider='mymemory+fallback'):
    """Create a candidate translation first; publish it atomically and retain history."""
    article = type(article).objects.select_for_update().get(pk=article.pk)
    source_text = article.full_text
    if full_text and not source_text and article.pdf:
        source_text = extract_pdf_text(article)
    source_hash = hashlib.sha256(f'{article.title}\n{article.abstract}\n{source_text}'.encode('utf-8')).hexdigest()
    if not force and article.translation_hash == source_hash and article.translation_status in {'translated', 'reviewed'}:
        return article

    try:
        title_fa = translate_text(article.title) if (force or not article.title_fa) else article.title_fa
        abstract_fa = translate_text(article.abstract) if article.abstract and (force or not article.abstract_fa) else article.abstract_fa
        content_fa = translate_text(source_text) if full_text and source_text and (force or not article.full_text_fa) else article.full_text_fa
        if not title_fa.strip():
            raise ValueError('Translation produced an empty Persian title')
        if full_text and source_text and not content_fa.strip():
            raise ValueError('Translation produced empty Persian content')
    except Exception as exc:
        article.translation_status = 'failed'
        article.translation_error = str(exc)[:4000]
        article.save(update_fields=['translation_status', 'translation_error', 'updated_at'])
        return article

    next_version = article.translation_version + 1
    ArticleTranslationVersion.objects.create(
        article=article, version=next_version, title_fa=title_fa, abstract_fa=abstract_fa,
        content_fa=content_fa, provider=provider, source_hash=source_hash, is_valid=True,
    )
    article.title_fa = title_fa
    article.abstract_fa = abstract_fa
    if source_text:
        article.full_text = source_text
    if full_text:
        article.full_text_fa = content_fa
    article.translation_status = 'translated'
    article.translation_hash = source_hash
    article.translation_version = next_version
    article.translation_error = ''
    article.translated_at = timezone.now()
    article.save()
    return article

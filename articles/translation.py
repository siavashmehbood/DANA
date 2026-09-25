import hashlib
import re
import time
import threading
import ipaddress
import socket
from urllib.parse import urlparse

import pymupdf
import requests
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .models import ArticleTranslationVersion

MYMEMORY_URL = 'https://api.mymemory.translated.net/get'
_PROVIDER_COOLDOWN = {}
_PROVIDER_LOCK = threading.Lock()
_ARGOS_READY = False


def _cooldown_active(provider):
    with _PROVIDER_LOCK:
        return _PROVIDER_COOLDOWN.get(provider, 0) > time.monotonic()


def _cooldown(provider, seconds):
    with _PROVIDER_LOCK:
        _PROVIDER_COOLDOWN[provider] = max(_PROVIDER_COOLDOWN.get(provider, 0), time.monotonic() + seconds)


def _argos_translate(text):
    global _ARGOS_READY
    import argostranslate.package
    import argostranslate.translate
    if not _ARGOS_READY:
        installed = argostranslate.translate.get_installed_languages()
        en = next((lang for lang in installed if lang.code == 'en'), None)
        fa = next((lang for lang in installed if lang.code == 'fa'), None)
        if not en or not fa:
            argostranslate.package.update_package_index()
            package = next((p for p in argostranslate.package.get_available_packages() if p.from_code == 'en' and p.to_code == 'fa'), None)
            if not package:
                raise RuntimeError('Argos en->fa model is unavailable')
            argostranslate.package.install_from_path(package.download())
        _ARGOS_READY = True
    return _normalize_translation(argostranslate.translate.translate(text, 'en', 'fa'))

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


def _safe_remote_url(url):
    parsed=urlparse(url or '')
    if parsed.scheme not in {'http','https'} or not parsed.hostname:
        return False
    if parsed.hostname.lower() in {'localhost','localhost.localdomain'}:
        return False
    try:
        addresses={info[4][0] for info in socket.getaddrinfo(parsed.hostname,parsed.port or (443 if parsed.scheme=='https' else 80),type=socket.SOCK_STREAM)}
        for address in addresses:
            ip=ipaddress.ip_address(address)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                return False
    except (socket.gaierror,ValueError):
        return False
    return True


def download_article_pdf(article, max_bytes=20 * 1024 * 1024):
    if article.pdf or not article.pdf_url:
        return False
    if not _safe_remote_url(article.pdf_url):
        raise ValueError('Unsafe PDF URL')
    response = requests.get(article.pdf_url, timeout=20, headers={'User-Agent': 'DANA/2.0'}, stream=True)
    response.raise_for_status()
    if not _safe_remote_url(response.url):
        response.close()
        raise ValueError('Unsafe PDF redirect target')
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


def _normalize_translation(text):
    value = re.sub(r'\s+', ' ', (text or '').replace('ي','ی').replace('ك','ک')).strip()
    return value


def _translation_quality(source, translated):
    translated = _normalize_translation(translated)
    if not source or not translated:
        return False
    # Scientific titles legitimately retain acronyms, model names, formulae and proper nouns.
    # Require meaningful Persian rather than an unrealistically high Persian-letter ratio.
    persian = len(re.findall(r'[\u0600-\u06FF]', translated))
    latin = len(re.findall(r'[A-Za-z]', translated))
    words = re.findall(r"[A-Za-z\u0600-\u06FF]+", translated)
    source_words = re.findall(r"[A-Za-z]+", source)
    min_persian = 2 if len(source_words) <= 4 else max(3, min(12, len(source_words) // 3))
    if persian < min_persian:
        return False
    # Mixed scientific Persian may retain acronyms/proper nouns, but prose that
    # remains predominantly English is not a usable translation.
    if latin > persian and latin > 8:
        return False
    if len(words) < max(1, min(4, len(source_words) // 4)):
        return False
    return True


def translate_text(text, delay=0.1, retries=3, return_provider=False):
    result, providers = [], []
    for chunk in _chunks(text):
        translated_chunk, used_provider = '', ''
        if not _cooldown_active('mymemory'):
            for attempt in range(retries):
                try:
                    response = requests.get(MYMEMORY_URL, params={'q': chunk, 'langpair': 'en|fa'}, timeout=8, headers={'User-Agent': 'DANA/2.0'})
                    if response.status_code == 429:
                        _cooldown('mymemory', 300); break
                    if response.status_code >= 500:
                        if attempt + 1 < retries:
                            time.sleep(min(2 ** attempt, 4)); continue
                        _cooldown('mymemory', 120); break
                    response.raise_for_status()
                    payload = response.json()
                    response_status = payload.get('responseStatus')
                    if response_status and int(response_status) >= 400:
                        _cooldown('mymemory', 300 if int(response_status) == 429 else 120); break
                    candidate = _normalize_translation(payload.get('responseData', {}).get('translatedText', ''))
                    if candidate and _translation_quality(chunk, candidate):
                        translated_chunk, used_provider = candidate, 'mymemory'; break
                    if attempt + 1 < retries: time.sleep(min(2 ** attempt, 4))
                except (requests.Timeout, requests.ConnectionError):
                    if attempt + 1 < retries: time.sleep(min(2 ** attempt, 4))
                    else: _cooldown('mymemory', 60)
                except (requests.RequestException, ValueError):
                    break
        if not translated_chunk:
            try:
                candidate = _argos_translate(chunk)
                if candidate and _translation_quality(chunk, candidate): translated_chunk, used_provider = candidate, 'argos-offline'
            except Exception:
                pass
        if not translated_chunk:
            fallback = _normalize_translation(rough_translate(chunk))
            if fallback != _normalize_translation(chunk) and _translation_quality(chunk, fallback): translated_chunk, used_provider = fallback, 'rough-glossary'
            else: raise RuntimeError('Translation providers exhausted without a valid Persian translation')
        result.append(translated_chunk); providers.append(used_provider); time.sleep(delay)
    value = '\n\n'.join(result)
    provenance = '+'.join(dict.fromkeys(providers))
    return (value, provenance) if return_provider else value


def translate_article(article, full_text=False, force=False, provider=None, created_by=None):
    """Translate outside a DB transaction, then publish a validated version atomically.

    Network translation used to run while holding select_for_update(), which could
    block article/admin requests for many seconds.  Only the final version publish
    is serialized now; source changes during translation are detected and retried.
    """
    model=type(article)
    article=model.objects.get(pk=article.pk)
    source_text=article.full_text
    if full_text and not source_text and article.pdf:
        source_text=extract_pdf_text(article)
    source_title, source_abstract = article.title, article.abstract
    source_hash=hashlib.sha256(f'{source_title}\n{source_abstract}\n{source_text}'.encode('utf-8')).hexdigest()
    coverage_complete = (
        bool(article.title_fa)
        and (not source_abstract or bool(article.abstract_fa))
        and (not full_text or not source_text or bool(article.full_text_fa))
    )
    if not force and coverage_complete and article.translation_hash == source_hash and article.translation_status in {'translated','reviewed'}:
        return article

    model.objects.filter(pk=article.pk).update(translation_status='translating',translation_error='')
    try:
        used_providers=[]
        def translated_value(source, existing, needed=True):
            if not needed or (existing and not force): return existing
            value, used = translate_text(source, return_provider=True)
            if used: used_providers.extend(used.split('+'))
            return value
        title_fa=translated_value(source_title, article.title_fa)
        abstract_fa=translated_value(source_abstract, article.abstract_fa, bool(source_abstract))
        content_fa=translated_value(source_text, article.full_text_fa, bool(full_text and source_text))

        if not _translation_quality(source_title,title_fa):
            raise ValueError('Translation quality validation failed for title')
        if source_abstract and not _translation_quality(source_abstract,abstract_fa):
            raise ValueError('Translation quality validation failed for abstract')
        if full_text and source_text and not _translation_quality(source_text,content_fa):
            raise ValueError('Translation quality validation failed for content')
    except Exception as exc:
        message=str(exc)
        status='validation_failed' if message.startswith('Translation quality validation failed') else 'provider_failed'
        model.objects.filter(pk=article.pk).update(translation_status=status,translation_error=message[:4000],updated_at=timezone.now())
        return model.objects.get(pk=article.pk)

    with transaction.atomic():
        locked=model.objects.select_for_update().get(pk=article.pk)
        current_text=locked.full_text or (source_text if full_text else locked.full_text)
        current_hash=hashlib.sha256(f'{locked.title}\n{locked.abstract}\n{current_text}'.encode('utf-8')).hexdigest()
        if locked.title != source_title or locked.abstract != source_abstract or current_hash != source_hash:
            locked.translation_status='pending'
            locked.translation_error='منبع مقاله هنگام ترجمه تغییر کرد؛ ترجمه باید دوباره اجرا شود.'
            locked.save(update_fields=['translation_status','translation_error','updated_at'])
            return locked
        next_version=(locked.translation_versions.aggregate(max_version=Max('version'))['max_version'] or 0)+1
        ArticleTranslationVersion.objects.create(
            article=locked,version=next_version,title_fa=title_fa,abstract_fa=abstract_fa,
            content_fa=content_fa,provider=provider or '+'.join(dict.fromkeys(used_providers)) or 'existing-translation',quality_score=100,source_hash=source_hash,
            is_valid=True,created_by=created_by,
        )
        locked.title_fa=title_fa
        locked.abstract_fa=abstract_fa
        if full_text and source_text:
            locked.full_text=source_text
            locked.full_text_fa=content_fa
        locked.translation_status='original_only' if (not full_text and bool(locked.full_text)) else 'translated'
        locked.translation_hash=source_hash
        locked.translation_version=next_version
        locked.translation_quality=100
        locked.translation_error=''
        locked.translated_at=timezone.now()
        locked.save()
        return locked

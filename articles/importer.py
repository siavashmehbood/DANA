import hashlib
import logging
import re
import time
from datetime import datetime, timezone

import requests
from django.utils.text import slugify

from .models import Article, ArticleSource

logger = logging.getLogger(__name__)

OPENALEX_URL = 'https://api.openalex.org/works'
CROSSREF_URL = 'https://api.crossref.org/works'
S2_URL = 'https://api.semanticscholar.org/graph/v1/paper/search'
ARXIV_URL = 'https://export.arxiv.org/api/query'


def _get(url, *, params=None, headers=None, timeout=25, retries=3):
    last_error = None
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            if response.status_code == 429:
                # Do not stall an entire discovery cycle when one provider is rate limited.
                last_error = requests.HTTPError("429 rate limited", response=response)
                break
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(min(2 ** attempt, 8))
    if last_error:
        raise last_error
    raise RuntimeError("request failed")


def _norm(value):
    return re.sub(r'\s+', ' ', (value or '').strip().lower())


def _abstract(index):
    if not index:
        return ''
    words = [(pos, word) for word, positions in index.items() for pos in positions]
    return ' '.join(word for _, word in sorted(words))


def _authors(items):
    names = []
    for item in items or []:
        author = item.get('author') or item.get('name') or {}
        name = author.get('display_name') if isinstance(author, dict) else author
        if name:
            names.append(name)
    return ', '.join(dict.fromkeys(names))


def _best_pdf(locations):
    for location in locations or []:
        if location.get('is_oa') and location.get('pdf_url'):
            return location['pdf_url']
    for location in locations or []:
        if location.get('pdf_url'):
            return location['pdf_url']
    return ''


def _slug(title, identity):
    # URL patterns are intentionally ASCII-only, so never persist Unicode slugs.
    base = slugify(title, allow_unicode=False)[:450] or 'article'
    return f'{base}-{hashlib.sha1(identity.encode()).hexdigest()[:10]}'


def _score(item):
    score = 0.0
    score += min(float(item.get('citation_count') or 0), 5000) / 100
    if item.get('pdf_url'):
        score += 20
    if item.get('abstract'):
        score += 10
    year = item.get('year')
    if year:
        age = max(datetime.now(timezone.utc).year - int(year), 0)
        score += max(0, 20 - age * 2)
    return round(score, 2)


def _openalex(query, limit):
    data = _get(OPENALEX_URL, params={'search': query, 'per-page': min(limit, 200), 'filter': 'type:article'}).json()
    results = []
    for work in data.get('results', []):
        title = (work.get('display_name') or '').strip()
        if not title:
            continue
        results.append({
            'provider': 'openalex', 'external_id': work.get('id', ''),
            'title': title, 'authors': _authors(work.get('authorships')),
            'abstract': _abstract(work.get('abstract_inverted_index')),
            'year': work.get('publication_year'), 'publication_date': work.get('publication_date'),
            'journal': ((work.get('primary_location') or {}).get('source') or {}).get('display_name', ''),
            'doi': (work.get('doi') or '').strip(), 'source_url': work.get('id', ''),
            'pdf_url': _best_pdf(work.get('locations')),
            'citation_count': work.get('cited_by_count', 0),
        })
    return results


def _crossref(query, limit):
    data = _get(CROSSREF_URL, params={'query.bibliographic': query, 'rows': min(limit, 100),
                                      'select': 'DOI,title,author,published,container-title,URL,abstract,link'}).json()
    results = []
    for work in data.get('message', {}).get('items', []):
        title = ((work.get('title') or [''])[0]).strip()
        if not title:
            continue
        published = work.get('published-print') or work.get('published-online') or work.get('published') or {}
        parts = published.get('date-parts') or [[]]
        pdf_url = ''
        for link in work.get('link') or []:
            if (link.get('content-type') or '').lower() == 'application/pdf' and link.get('URL'):
                pdf_url = link['URL']
                break
        results.append({
            'provider': 'crossref', 'external_id': work.get('DOI', ''), 'title': title,
            'authors': _authors(work.get('author')), 'abstract': re.sub('<[^>]+>', ' ', work.get('abstract', '') or ''),
            'year': (parts[0] or [None])[0], 'publication_date': '-'.join(str(x).zfill(2) if i else str(x) for i, x in enumerate(parts[0])) if parts and parts[0] else None,
            'journal': ((work.get('container-title') or [''])[0]), 'doi': work.get('DOI', ''),
            'source_url': work.get('URL', ''), 'pdf_url': pdf_url, 'citation_count': 0,
        })
    return results


def _semantic(query, limit):
    data = _get(S2_URL, params={'query': query, 'limit': min(limit, 100),
                                'fields': 'title,abstract,authors,year,venue,externalIds,citationCount,url,openAccessPdf'}).json()
    results = []
    for work in data.get('data', []):
        title = (work.get('title') or '').strip()
        if not title:
            continue
        ids = work.get('externalIds') or {}
        oa = work.get('openAccessPdf') or {}
        results.append({
            'provider': 'semantic_scholar', 'external_id': work.get('paperId', ''), 'title': title,
            'authors': _authors(work.get('authors')), 'abstract': work.get('abstract') or '',
            'year': work.get('year'), 'publication_date': None, 'journal': work.get('venue') or '',
            'doi': ids.get('DOI', ''), 'source_url': work.get('url') or '',
            'pdf_url': oa.get('url') or '', 'citation_count': work.get('citationCount') or 0,
        })
    return results


def discover_articles(query, limit=20, providers=None):
    providers = providers or ['openalex', 'semantic_scholar', 'crossref']
    per_source = max(5, min(int(limit), 100))
    rows = []
    for provider in providers:
        try:
            if provider == 'openalex':
                rows.extend(_openalex(query, per_source))
            elif provider == 'semantic_scholar':
                rows.extend(_semantic(query, per_source))
            elif provider == 'crossref':
                rows.extend(_crossref(query, per_source))
        except Exception as exc:
            logger.warning('article discovery failed for %s: %s', provider, exc)
    unique = {}
    for row in rows:
        key = f"doi:{_norm(row.get('doi'))}" if row.get('doi') else f"title:{_norm(row.get('title'))}"
        if key.startswith('doi:') and key == 'doi:':
            key = f"title:{_norm(row.get('title'))}"
        old = unique.get(key)
        if not old or (row.get('citation_count', 0) or 0) > (old.get('citation_count', 0) or 0):
            unique[key] = row
    rows = list(unique.values())
    for row in rows:
        row['relevance_score'] = _score(row)
    rows.sort(key=lambda item: (item['relevance_score'], item.get('year') or 0), reverse=True)
    return rows[: int(limit)]


def import_discovered(query, limit=20, category=None, providers=None):
    created = updated = 0
    source_cache = {}
    discovered = discover_articles(query, limit, providers)
    for item in discovered:
        # Never publish a metadata-only record as a readable article.
        # A record is importable only when we have text/abstract or a PDF source.
        has_content = any((item.get(field) or '').strip() for field in ('abstract', 'full_text', 'full_text_fa', 'pdf_url'))
        if not has_content:
            logger.info('Skipping metadata-only article: %s', item.get('title', ''))
            continue
        identity = item.get('doi') or item.get('external_id') or item['title']
        provider = item.get('provider', '')
        if provider not in source_cache:
            source_cache[provider], _ = ArticleSource.objects.get_or_create(name=provider or 'unknown', defaults={'source_type': 'api', 'is_active': True})
        defaults = {
            'title': item['title'], 'slug': _slug(item['title'], identity),
            'authors': item.get('authors', ''), 'abstract': item.get('abstract', ''),
            'year': item.get('year'), 'publication_date': item.get('publication_date'), 'journal': item.get('journal', ''),
            'doi': item.get('doi', ''), 'source_url': item.get('source_url', ''),
            'pdf_url': item.get('pdf_url', ''), 'category': category,
            'access': 'open' if item.get('pdf_url') else 'external', 'published': True,
            'external_id': item.get('external_id', ''), 'source_provider': provider, 'source': source_cache[provider],
            'citation_count': item.get('citation_count') or 0,
            'relevance_score': item.get('relevance_score') or 0,
        }
        obj = Article.objects.filter(doi=defaults['doi']).first() if defaults['doi'] else None
        if not obj and defaults['external_id']:
            obj = Article.objects.filter(external_id=defaults['external_id'], source_provider=defaults['source_provider']).first()
        if not obj:
            obj = Article.objects.filter(title__iexact=defaults['title']).first()
        if obj:
            for key, value in defaults.items():
                if value not in ('', None):
                    setattr(obj, key, value)
            obj.last_discovered_at = datetime.now(timezone.utc)
            obj.save()
            updated += 1
        else:
            defaults['last_discovered_at'] = datetime.now(timezone.utc)
            Article.objects.create(**defaults)
            created += 1
    return {'created': created, 'updated': updated, 'discovered': len(discovered)}


# Backwards-compatible API used by the existing management command.
def import_openalex(query, limit=20, category=None):
    return import_discovered(query, limit, category, providers=['openalex'])

import hashlib
import requests
from django.utils.text import slugify
from .models import Article

OPENALEX = 'https://api.openalex.org/works'


def search_openalex(query, limit=20):
    params = {'search': query, 'per-page': min(int(limit), 200)}
    response = requests.get(OPENALEX, params=params, timeout=20)
    response.raise_for_status()
    return response.json().get('results', [])


def _best_pdf(work):
    for location in work.get('locations') or []:
        if location.get('is_oa') and location.get('pdf_url'):
            return location['pdf_url']
    return ''


def _authors(work):
    names = []
    for item in work.get('authorships', []):
        name = (item.get('author') or {}).get('display_name')
        if name:
            names.append(name)
    return ', '.join(names)


def _abstract(index):
    if not index:
        return ''
    words = [(pos, word) for word, positions in index.items() for pos in positions]
    return ' '.join(word for _, word in sorted(words))


def _slug(title, work_id):
    base = slugify(title, allow_unicode=True)[:450]
    return f'{base}-{hashlib.sha1(work_id.encode()).hexdigest()[:10]}'


def import_openalex(query, limit=20, category=None):
    created = updated = 0
    for work in search_openalex(query, limit):
        title = (work.get('display_name') or '').strip()
        if not title:
            continue
        doi = (work.get('doi') or '').strip()
        work_id = work.get('id') or title
        pdf_url = _best_pdf(work)
        defaults = {
            'title': title, 'slug': _slug(title, work_id),
            'authors': _authors(work), 'abstract': _abstract(work.get('abstract_inverted_index')),
            'year': work.get('publication_year'),
            'journal': ((work.get('primary_location') or {}).get('source') or {}).get('display_name', ''),
            'doi': doi, 'source_url': work_id, 'pdf_url': pdf_url,
            'category': category, 'access': 'open' if pdf_url else 'external', 'published': True,
        }
        obj = Article.objects.filter(doi=doi).first() if doi else None
        if not obj:
            obj = Article.objects.filter(source_url=work_id).first()
        if obj:
            for key, value in defaults.items():
                setattr(obj, key, value)
            obj.save()
            updated += 1
        else:
            Article.objects.create(**defaults)
            created += 1
    return {'created': created, 'updated': updated}

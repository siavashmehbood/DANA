import json
import logging

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.template.defaultfilters import linebreaks

from .models import Article, ArticleCategory, ArticleLibraryItem, ArticleAnnotation
logger = logging.getLogger(__name__)


from .translation import (
    download_article_pdf,
    extract_pdf_text,
    rough_translate,
    translate_article,
)


def listing(request):
    query = request.GET.get('q', '').strip()[:200]
    category = request.GET.get('category', '').strip()
    sort = request.GET.get('sort', 'top').strip()
    saved_only = request.GET.get('saved') == '1' and request.user.is_authenticated
    # Only show articles that have something the reader can actually open:
    # full text, translated text, an abstract, or a PDF source.
    readable = Q(full_text__gt='') | Q(full_text_fa__gt='') | Q(abstract__gt='') | Q(abstract_fa__gt='') | Q(pdf_url__gt='') | Q(pdf__gt='')
    articles = Article.objects.filter(published=True).filter(readable).select_related('category')
    if saved_only:
        articles = articles.filter(library_items__user=request.user)
    if query:
        query = query.replace('ي','ی').replace('ك','ک').replace('\u200c',' ')
        articles = articles.filter(
            Q(title__icontains=query) | Q(title_fa__icontains=query) |
            Q(authors__icontains=query) | Q(abstract__icontains=query) |
            Q(abstract_fa__icontains=query) | Q(full_text__icontains=query) |
            Q(full_text_fa__icontains=query) | Q(journal__icontains=query) |
            Q(doi__icontains=query)
        )
    if category:
        articles = articles.filter(category__slug=category)
    if sort == 'popular':
        articles = articles.order_by('-downloads', '-citation_count', '-relevance_score', '-year', '-created_at')
    elif sort == 'top':
        articles = articles.order_by('-relevance_score', '-citation_count', '-downloads', '-year', '-created_at')
    elif sort == 'oldest':
        articles = articles.order_by('year', 'created_at')
    else:
        articles = articles.order_by('-created_at')
    paginator = Paginator(articles, 100)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    for article in page_obj.object_list:
        article.display_title = article.title_fa or rough_translate(article.title)
        article.display_abstract = article.abstract_fa or rough_translate(article.abstract)
    return render(request, 'articles/list.html', {
        'articles': page_obj.object_list, 'page_obj': page_obj,
        'categories': ArticleCategory.objects.filter(is_active=True),
        'query': query, 'selected_category': category,
        'selected_sort': sort, 'article_count': paginator.count, 'saved_only': saved_only,
    })


def article_download(request, slug):
    article = get_object_or_404(Article.objects.select_related('source'), slug=slug, published=True)
    if article.source_id and not article.source.allow_full_republish:
        return JsonResponse({'error': 'دریافت فایل کامل طبق سیاست منبع مجاز نیست.'}, status=403)
    if not article.pdf:
        return JsonResponse({'error': 'فایل PDF برای این مقاله موجود نیست.'}, status=404)
    return FileResponse(article.pdf.open('rb'), as_attachment=True, filename=f'{article.slug}.pdf')


def detail(request, slug):
    readable = Q(full_text__gt='') | Q(full_text_fa__gt='') | Q(abstract__gt='') | Q(abstract_fa__gt='') | Q(pdf_url__gt='') | Q(pdf__gt='')
    article = get_object_or_404(
        Article.objects.select_related('category').filter(readable), slug=slug, published=True
    )
    # Keep detail pages fast: no network I/O during page rendering.
    mode = request.GET.get('lang', 'fa')
    if mode not in {'en', 'fa', 'both'}:
        mode = 'fa'
    search = request.GET.get('find', '').strip()
    article.reader_full_text = linebreaks(article.full_text or '')
    article.reader_full_text_fa = linebreaks(article.full_text_fa or '')
    if mode == 'fa' and not (article.full_text_fa or article.abstract_fa):
        mode = 'en'
    related = Article.objects.filter(published=True).exclude(pk=article.pk)
    if article.category_id:
        related = related.filter(category_id=article.category_id)
    related = related.order_by('-featured', '-year', '-created_at')[:4]
    library_item = None
    annotations = []
    if request.user.is_authenticated:
        library_item = ArticleLibraryItem.objects.filter(user=request.user, article=article).first()
        annotations = ArticleAnnotation.objects.filter(user=request.user, article=article)
    return render(request, 'articles/detail.html', {
        'article': article, 'related_articles': related,
        'language_mode': mode, 'reader_search': search,
        'library_item': library_item, 'annotations': annotations,
    })


@login_required
def pdf_reader(request, slug):
    article = get_object_or_404(Article, slug=slug, published=True)
    if not article.pdf and article.pdf_url:
        try:
            download_article_pdf(article)
        except Exception:
            logger.warning('Unable to download article PDF for reader: %s', article.slug, exc_info=True)
    if not article.pdf:
        return redirect('article_detail', slug=article.slug)
    item = ArticleLibraryItem.objects.filter(user=request.user, article=article).first()
    annotations = list(ArticleAnnotation.objects.filter(user=request.user, article=article).values('id', 'kind', 'selected_text', 'note', 'color', 'page', 'rects', 'text_prefix', 'text_suffix', 'created_at'))
    for annotation in annotations:
        annotation['created_at'] = annotation['created_at'].isoformat()
    return render(request, 'articles/pdf_reader.html', {
        'article': article,
        'pdf_url': reverse('article_download', args=[article.slug]),
        'annotations_json': json.dumps(annotations, ensure_ascii=False),
        'last_position': item.last_position if item else 0,
        'reading_seconds': item.reading_seconds if item else 0,
        'bookmarks_json': json.dumps((item.bookmarks if item else []), ensure_ascii=False),
    })


@login_required
def research_library(request):
    items = ArticleLibraryItem.objects.filter(user=request.user).select_related('article', 'article__category')
    status = request.GET.get('status', '').strip()
    favorite = request.GET.get('favorite') == '1'
    q = request.GET.get('q', '').strip()
    if status in dict(ArticleLibraryItem.STATUS_CHOICES):
        items = items.filter(status=status)
    if favorite:
        items = items.filter(favorite=True)
    if q:
        items = items.filter(Q(article__title__icontains=q) | Q(article__title_fa__icontains=q) | Q(article__authors__icontains=q) | Q(article__journal__icontains=q))
    annotations = ArticleAnnotation.objects.filter(user=request.user).select_related('article')
    stats = {
        'total': ArticleLibraryItem.objects.filter(user=request.user).count(),
        'reading': ArticleLibraryItem.objects.filter(user=request.user, status='reading').count(),
        'read': ArticleLibraryItem.objects.filter(user=request.user, status='read').count(),
        'favorites': ArticleLibraryItem.objects.filter(user=request.user, favorite=True).count(),
    }
    return render(request, 'articles/library.html', {'items': items[:100], 'annotations': annotations[:40], 'stats': stats, 'status': status, 'favorite': favorite, 'query': q})


@login_required
@require_POST
def annotation_delete(request, pk):
    item = get_object_or_404(ArticleAnnotation, pk=pk, user=request.user)
    item.delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def reading_progress(request, slug):
    article = get_object_or_404(Article, slug=slug, published=True)
    item, _ = ArticleLibraryItem.objects.get_or_create(user=request.user, article=article)
    try:
        item.progress = max(0, min(100, int(request.POST.get('progress', 0))))
        item.last_position = max(0, int(request.POST.get('position', 0)))
        item.reading_seconds = min(31536000, max(0, int(request.POST.get('seconds', item.reading_seconds))))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False}, status=400)
    item.last_read_at = timezone.now()
    if item.progress >= 95:
        item.status = 'read'
    elif item.progress > 0 and item.status == 'unread':
        item.status = 'reading'
    item.save(update_fields=['progress','last_position','reading_seconds','last_read_at','status','updated_at'])
    return JsonResponse({'ok': True, 'progress': item.progress})


def citation_export(request, slug):
    article = get_object_or_404(Article, slug=slug, published=True)
    fmt = request.GET.get('format', 'bibtex').lower()
    title = article.title or ''
    authors = article.authors or 'Unknown'
    year = article.year or ''
    key = ''.join(c for c in (title.split()[0] if title.split() else 'article') if c.isalnum()) + str(year)
    if fmt == 'bibtex':
        body = '@article{%s,\n  title={%s},\n  author={%s},\n  year={%s},\n  journal={%s},\n  doi={%s}\n}' % (key, title, authors, year, article.journal, article.doi)
        content_type, filename = 'application/x-bibtex; charset=utf-8', f'{article.slug}.bib'
    elif fmt == 'ris':
        body = 'TY  - JOUR\nTI  - %s\nAU  - %s\nPY  - %s\nJO  - %s\nDO  - %s\nER  -' % (title, authors, year, article.journal, article.doi)
        content_type, filename = 'application/x-research-info-systems; charset=utf-8', f'{article.slug}.ris'
    elif fmt == 'ieee':
        body = '%s, "%s," %s, %s%s.' % (authors, title, article.journal, year, (', doi: '+article.doi) if article.doi else '')
        content_type, filename = 'text/plain; charset=utf-8', f'{article.slug}-ieee.txt'
    else:
        body = '%s. (%s). %s. %s.%s' % (authors, year, title, article.journal, (' https://doi.org/'+article.doi) if article.doi else '')
        content_type, filename = 'text/plain; charset=utf-8', f'{article.slug}-apa.txt'
    response = HttpResponse(body, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_POST
def library_action(request, slug):
    article = get_object_or_404(Article, slug=slug, published=True)
    item, _ = ArticleLibraryItem.objects.get_or_create(user=request.user, article=article)
    action = request.POST.get('action', 'toggle')
    if action == 'status':
        item.status = request.POST.get('status', item.status)
        if item.status not in dict(ArticleLibraryItem.STATUS_CHOICES):
            return JsonResponse({'ok': False, 'error': 'وضعیت نامعتبر است.'}, status=400)
    elif action == 'favorite':
        item.favorite = not item.favorite
    elif action == 'progress':
        try:
            item.progress = max(0, min(100, int(request.POST.get('progress', item.progress))))
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'error': 'درصد پیشرفت نامعتبر است.'}, status=400)
    item.save()
    return JsonResponse({'ok': True, 'status': item.status, 'favorite': item.favorite, 'progress': item.progress})


@login_required
@require_POST
def annotation_create(request, slug):
    article = get_object_or_404(Article, slug=slug, published=True)
    selected = request.POST.get('selected_text', '').strip()[:12000]
    if not selected:
        return JsonResponse({'ok': False, 'error': 'متنی انتخاب نشده است.'}, status=400)
    kind = request.POST.get('kind', 'highlight')
    if kind not in {'highlight', 'note'}:
        kind = 'highlight'
    try:
        page = max(0, int(request.POST.get('page', 0)))
    except (TypeError, ValueError):
        page = 0
    try:
        rects = json.loads(request.POST.get('rects', '[]')) if request.POST.get('rects') else []
    except (TypeError, ValueError, json.JSONDecodeError):
        rects = []
    valid_colors = {'amber', 'green', 'blue', 'red', 'purple'}
    color = request.POST.get('color', 'amber').strip().lower()
    if color not in valid_colors:
        color = 'amber'
    clean_rects = []
    if isinstance(rects, list):
        for rect in rects[:100]:
            if not isinstance(rect, dict):
                continue
            try:
                clean = {
                    'page': max(1, int(rect.get('page', page or 1))),
                    'x': min(1, max(0, float(rect.get('x', 0)))),
                    'y': min(1, max(0, float(rect.get('y', 0)))),
                    'w': min(1, max(0, float(rect.get('w', 0)))),
                    'h': min(1, max(0, float(rect.get('h', 0)))),
                }
            except (TypeError, ValueError):
                continue
            if clean['w'] > 0 and clean['h'] > 0:
                clean_rects.append(clean)
    item = ArticleAnnotation.objects.create(
        user=request.user, article=article, kind=kind,
        selected_text=selected, note=request.POST.get('note', '').strip()[:5000],
        color=color, text_prefix=request.POST.get('prefix', '').strip()[:300],
        rects=clean_rects, text_suffix=request.POST.get('suffix', '').strip()[:300], page=page,
    )
    return JsonResponse({'ok': True, 'id': item.id, 'kind': item.kind, 'selected_text': item.selected_text, 'note': item.note})


@login_required
@require_POST
def annotation_update(request, pk):
    item = get_object_or_404(ArticleAnnotation, pk=pk, user=request.user)
    note = request.POST.get('note', '').strip()[:5000]
    color = request.POST.get('color', item.color).strip().lower()
    if color not in {'amber', 'green', 'blue', 'red', 'purple'}:
        color = item.color
    item.note = note
    item.color = color
    item.save(update_fields=['note', 'color', 'updated_at'])
    return JsonResponse({'ok': True, 'id': item.id, 'note': item.note, 'color': item.color})


@login_required
@require_POST
def bookmark_toggle(request, slug):
    article = get_object_or_404(Article, slug=slug, published=True)
    try:
        page = max(1, int(request.POST.get('page', 1)))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'invalid_page'}, status=400)
    item, _ = ArticleLibraryItem.objects.get_or_create(user=request.user, article=article)
    bookmarks = sorted({int(x) for x in item.bookmarks if str(x).isdigit()})
    if page in bookmarks:
        bookmarks.remove(page)
        active = False
    else:
        bookmarks.append(page)
        bookmarks.sort()
        active = True
    item.bookmarks = bookmarks[:500]
    item.save(update_fields=['bookmarks', 'updated_at'])
    return JsonResponse({'ok': True, 'page': page, 'active': active, 'bookmarks': item.bookmarks})


@require_POST
def translate_selection(request, slug):
    article = get_object_or_404(Article, slug=slug, published=True)
    text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({'ok': False, 'error': 'متنی انتخاب نشده است.'}, status=400)
    if len(text) > 1000:
        return JsonResponse({'ok': False, 'error': 'متن انتخابی بیش از حد طولانی است.'}, status=400)
    return JsonResponse({
        'ok': False,
        'available': bool(article.full_text_fa),
        'error': 'ترجمه خودکار این عبارت هنوز به سرویس ترجمه متصل نیست.',
    }, status=503)

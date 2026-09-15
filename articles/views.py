from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Article, ArticleCategory
from .translation import (
    download_article_pdf,
    extract_pdf_text,
    rough_translate,
    translate_article,
)


def listing(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    sort = request.GET.get('sort', 'newest').strip()
    articles = Article.objects.filter(published=True).select_related('category')
    if query:
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
        articles = articles.order_by('-downloads', '-year', '-created_at')
    elif sort == 'oldest':
        articles = articles.order_by('year', 'created_at')
    else:
        articles = articles.order_by('-created_at')
    paginator = Paginator(articles, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    for article in page_obj.object_list:
        article.display_title = article.title_fa or rough_translate(article.title)
        article.display_abstract = article.abstract_fa or rough_translate(article.abstract)
    return render(request, 'articles/list.html', {
        'articles': page_obj.object_list, 'page_obj': page_obj,
        'categories': ArticleCategory.objects.filter(is_active=True),
        'query': query, 'selected_category': category,
        'selected_sort': sort, 'article_count': paginator.count,
    })


def article_download(request, slug):
    article = get_object_or_404(Article, slug=slug, published=True)
    if not article.pdf:
        return JsonResponse({'error': 'فایل PDF برای این مقاله موجود نیست.'}, status=404)
    return FileResponse(article.pdf.open('rb'), as_attachment=True, filename=f'{article.slug}.pdf')


def detail(request, slug):
    article = get_object_or_404(
        Article.objects.select_related('category'), slug=slug, published=True
    )
    if not article.pdf and article.pdf_url:
        try:
            download_article_pdf(article)
        except Exception:
            # A missing or protected PDF should not break article reading.
            pass
    if article.pdf and not article.full_text:
        try:
            extracted = extract_pdf_text(article)
            if extracted:
                article.full_text = extracted
                article.save(update_fields=['full_text', 'updated_at'])
        except Exception:
            pass
    if (
        not article.title_fa
        or (article.abstract and not article.abstract_fa)
        or (article.full_text and not article.full_text_fa)
    ):
        try:
            translate_article(article, full_text=True)
        except Exception:
            # The article remains usable if the external translator is unavailable.
            pass
    mode = request.GET.get('lang', 'fa')
    if mode not in {'en', 'fa', 'both'}:
        mode = 'fa'
    search = request.GET.get('find', '').strip()
    related = Article.objects.filter(published=True).exclude(pk=article.pk)
    if article.category_id:
        related = related.filter(category_id=article.category_id)
    related = related.order_by('-featured', '-year', '-created_at')[:4]
    return render(request, 'articles/detail.html', {
        'article': article, 'related_articles': related,
        'language_mode': mode, 'reader_search': search,
    })


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

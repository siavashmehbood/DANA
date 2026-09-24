from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.utils import timezone

from shop.models import Entitlement
from .models import Book, Category
from core.text_utils import search_variants


def _public_books():
    now = timezone.now()
    return Book.objects.filter(status='published').filter(
        Q(publish_at__isnull=True) | Q(publish_at__lte=now)
    ).select_related('author', 'category', 'level')


def listing(request):
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('cat', '').strip()
    sort = request.GET.get('sort', 'new')
    if sort not in {'new', 'price_low', 'price_high'}:
        sort = 'new'

    books = _public_books()
    if q:
        search_q = Q()
        for variant in search_variants(q):
            search_q |= (
                Q(name__icontains=variant) |
                Q(author__name__icontains=variant) |
                Q(summary__icontains=variant) |
                Q(description__icontains=variant)
            )
        books = books.filter(search_q).distinct()

    if cat:
        books = books.filter(category__slug=cat)

    if sort == 'price_low':
        books = books.order_by('price', '-created_at')
    elif sort == 'price_high':
        books = books.order_by('-price', '-created_at')
    else:
        books = books.order_by('-created_at')

    paginator = Paginator(books, 24)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'books/list.html', {
        'books': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'cat': cat,
        'sort': sort,
        'categories': Category.objects.all(),
    })


def detail(request, slug):
    book = get_object_or_404(_public_books().prefetch_related('chapters'), slug=slug)
    related = _public_books().filter(category=book.category).exclude(pk=book.pk)[:4] if book.category else Book.objects.none()
    return render(request, 'books/detail.html', {'book': book, 'related': related})


def secure_file(request, pk, kind):
    book = get_object_or_404(_public_books(), pk=pk)
    if not request.user.is_authenticated:
        return HttpResponseForbidden('ورود لازم است.')
    if book.visibility != 'public' and not Entitlement.objects.filter(user=request.user, book=book).exists():
        return HttpResponseForbidden('دسترسی به این فایل ندارید.')
    field = {'pdf': book.pdf, 'audio': book.audio}.get(kind)
    if not field:
        return HttpResponseForbidden('فایل موجود نیست.')
    signer = TimestampSigner(salt='dana-secure-files')
    token = request.GET.get('token', '')
    expected = f'{request.user.pk}:{book.pk}:{kind}'
    try:
        if signer.unsign(token, max_age=3600) != expected:
            return HttpResponseForbidden('لینک فایل معتبر نیست یا منقضی شده است.')
    except (BadSignature, SignatureExpired):
        return HttpResponseForbidden('لینک فایل معتبر نیست یا منقضی شده است.')
    response = FileResponse(field.open('rb'), content_type='application/pdf' if kind == 'pdf' else 'audio/mpeg')
    response['Content-Disposition'] = f'inline; filename="{field.name.rsplit("/", 1)[-1]}"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response

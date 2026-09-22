from django.shortcuts import render,get_object_or_404
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
import mimetypes
from django.http import FileResponse, HttpResponseForbidden, Http404
from django.utils import timezone
from shop.models import Entitlement, Subscription
from analytics.models import Event
from reader.models import ReadingProgress
from .models import Book,Category

def _published_books():
    return Book.objects.filter(Q(status='published') | Q(status='scheduled', publish_at__lte=timezone.now()))

def listing(request):
    raw_q=request.GET.get('q','').strip()[:200]
    q=raw_q
    q=' '.join(q.replace('ي','ی').replace('ى','ی').replace('ك','ک').replace('\u200c',' ').replace('\u200f',' ').replace('\u200e',' ').split())
    cat=request.GET.get('cat','').strip()[:120].lower()
    category_qs=Category.objects.order_by('name')
    if cat and not category_qs.filter(slug=cat).exists(): cat=''
    sort=request.GET.get('sort','new')
    kind=request.GET.get('kind','all')
    price=request.GET.get('price','all')
    access=request.GET.get('access','all')
    if sort not in {'new','price_low','price_high','popular','rating','name'}: sort='new'
    if kind not in {'all','audio','text'}: kind='all'
    if price not in {'all','free','paid'}: price='all'
    if access not in {'all','subscription'}: access='all'
    books=_published_books().filter(visibility='public').select_related('author','category')

    def apply_filters(qs):
        if cat: qs=qs.filter(category__slug=cat)
        if kind=='audio': qs=qs.filter(Q(audio__gt='')|Q(chapters__audio__gt='')).distinct()
        elif kind=='text': qs=qs.filter(Q(pdf__gt='')|Q(chapters__text__gt='')).distinct()
        if access=='subscription': qs=qs.filter(subscription_included=True)
        if price=='free': qs=qs.filter(price=0)
        elif price=='paid': qs=qs.filter(price__gt=0)
        return qs

    def apply_sort(qs):
        if sort=='price_low': return qs.order_by('price','id')
        if sort=='price_high': return qs.order_by('-price','id')
        if sort=='popular': return qs.annotate(review_count=Count('review',filter=Q(review__approved=True))).order_by('-review_count','-created_at','-id')
        if sort=='rating': return qs.annotate(avg_rating=Avg('review__rating',filter=Q(review__approved=True))).order_by('-avg_rating','-created_at','-id')
        if sort=='name': return qs.order_by('name','id')
        return qs.order_by('-created_at','-id')
    if q:
        variants={q,q.replace('ی','ي').replace('ک','ك')}
        search_q=Q()
        for term in variants:
            search_q |= Q(name__icontains=term)|Q(author__name__icontains=term)|Q(summary__icontains=term)|Q(description__icontains=term)
        books=books.filter(search_q)
    books=apply_filters(books)
    books=apply_sort(books)
    total_count=books.count()
    page_number=request.GET.get('page','1')[:12]
    if not page_number.isdigit() or int(page_number) < 1: page_number='1'
    used_relaxed_search=False
    if q and total_count == 0:
        tokens=[t for t in q.split() if len(t)>1]
        relaxed=Q()
        for token in tokens:
            relaxed |= Q(name__icontains=token)|Q(author__name__icontains=token)|Q(summary__icontains=token)
        if relaxed:
            books=apply_sort(apply_filters(_published_books().filter(visibility='public').select_related('author','category').filter(relaxed)))
            total_count=books.count()
            used_relaxed_search=total_count > 0
        if total_count == 0 and page_number == '1':
            Event.objects.create(user=request.user if request.user.is_authenticated else None,name='search_zero_result',metadata={'query':q,'kind':kind,'price':price,'access':access,'category':cat,'sort':sort})
    if q and page_number == '1':
        Event.objects.create(user=request.user if request.user.is_authenticated else None,name='search',value=total_count,metadata={'query':q,'relaxed':used_relaxed_search,'kind':kind,'price':price,'access':access,'category':cat,'sort':sort})
    paginator=Paginator(books,24)
    page_obj=paginator.get_page(page_number)
    return render(request,'books/list.html',{'books':page_obj.object_list,'page_obj':page_obj,'total_count':total_count,'q':q,'cat':cat,'sort':sort,'kind':kind,'price':price,'access':access,'categories':category_qs,'used_relaxed_search':used_relaxed_search,'query_was_normalized':bool(raw_q and raw_q != q)})

def _has_book_access(user, book):
    if not user.is_authenticated:
        return False
    if book.visibility == 'password':
        return False
    if book.visibility == 'public' and book.price == 0:
        return True
    if Entitlement.objects.filter(user=user,book=book).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).exists():
        return True
    now=timezone.now()
    if not book.subscription_included:
        return False
    return Subscription.objects.filter(user=user,status='active',starts_at__lte=now,expires_at__gt=now,plan__grants_catalog_access=True).exists()


def detail(request,slug):
    book=get_object_or_404(_published_books().select_related('author','category','level').prefetch_related('chapters'),slug=slug)
    if book.visibility == 'password':
        raise Http404
    if book.visibility == 'private' and not book.subscription_included and not _has_book_access(request.user,book):
        raise Http404
    approved_reviews=book.review_set.filter(approved=True).select_related('user').order_by('-created_at')[:8]
    review_stats=book.review_set.filter(approved=True).aggregate(avg=Avg('rating'),count=Count('id'))
    related=_published_books().filter(visibility='public',category=book.category).exclude(pk=book.pk).select_related('author','category')[:4] if book.category else Book.objects.none()
    has_access = _has_book_access(request.user, book)
    saved_audio_seconds=0
    if request.user.is_authenticated and has_access:
        saved_audio_seconds=ReadingProgress.objects.filter(user=request.user,book=book).values_list('audio_seconds',flat=True).first() or 0
    response=render(request,'books/detail.html',{'book':book,'related':related,'has_access':has_access,'review_avg':review_stats['avg'],'review_count':review_stats['count'],'approved_reviews':approved_reviews,'saved_audio_seconds':saved_audio_seconds})
    if request.user.is_authenticated or book.visibility != 'public':
        response['Cache-Control']='private, no-store'
        response['Vary']='Cookie'
    if book.visibility != 'public':
        response['X-Robots-Tag']='noindex, nofollow'
    return response


def secure_file(request, pk, kind, chapter_id=None):
    if kind not in {'pdf','audio','chapter_audio'}:
        raise Http404
    if kind == 'chapter_audio' and chapter_id is None:
        raise Http404
    book = get_object_or_404(_published_books(), pk=pk)
    if not request.user.is_authenticated:
        response=HttpResponseForbidden('ورود لازم است.')
        response['Cache-Control']='private, no-store'
        response['X-Robots-Tag']='noindex, nofollow'
        return response
    if book.visibility == 'password':
        raise Http404
    if not _has_book_access(request.user, book):
        response=HttpResponseForbidden('دسترسی به این فایل ندارید.')
        response['Cache-Control']='private, no-store'
        response['X-Robots-Tag']='noindex, nofollow'
        return response
    if kind == 'chapter_audio':
        chapter = book.chapters.filter(pk=chapter_id).first()
        if chapter is None:
            raise Http404
        field = chapter.audio
    else:
        field = {'pdf': book.pdf, 'audio': book.audio}.get(kind)
    if not field:
        raise Http404
    content_type='application/pdf' if kind == 'pdf' else (mimetypes.guess_type(field.name)[0] or 'application/octet-stream')
    response = FileResponse(field.open('rb'), content_type=content_type)
    extension=field.name.rsplit('.',1)[-1].lower() if '.' in field.name else 'bin'
    response['Content-Disposition'] = f'inline; filename="book-{book.pk}-{kind}.{extension}"'
    try:
        response['Content-Length'] = str(field.size)
    except (OSError, ValueError):
        pass
    response['Cache-Control'] = 'private, no-store'
    response['Vary'] = 'Cookie'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cross-Origin-Resource-Policy'] = 'same-origin'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    response['Referrer-Policy'] = 'same-origin'
    if kind == 'pdf':
        response['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'self'; sandbox"
    return response

from django.shortcuts import render,get_object_or_404
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponseForbidden
from django.urls import reverse
from django.utils import timezone
from shop.models import Entitlement
from analytics.models import Event
from .models import Book,Category

def _published_books():
    return Book.objects.filter(Q(status='published') | Q(status='scheduled', publish_at__lte=timezone.now()))

def listing(request):
    q=request.GET.get('q','').strip()[:200]
    q=' '.join(q.replace('ي','ی').replace('ك','ک').replace('\u200c',' ').split()); cat=request.GET.get('cat','').strip(); sort=request.GET.get('sort','new'); kind=request.GET.get('kind','all'); price=request.GET.get('price','all')
    books=_published_books().select_related('author','category')
    if q and request.method == 'GET':
        Event.objects.create(user=request.user if request.user.is_authenticated else None,name='search',metadata={'query':q})
        variants={q,q.replace('ی','ي').replace('ک','ك')}
        search_q=Q()
        for term in variants:
            search_q |= Q(name__icontains=term)|Q(author__name__icontains=term)|Q(summary__icontains=term)|Q(description__icontains=term)
        books=books.filter(search_q)
    if cat: books=books.filter(category__slug=cat)
    if kind=='audio': books=books.filter(Q(audio__gt='')|Q(chapters__audio__gt='')).distinct()
    elif kind=='text': books=books.filter(Q(pdf__gt='')|Q(chapters__text__gt='')).distinct()
    if price=='free': books=books.filter(price=0)
    elif price=='paid': books=books.filter(price__gt=0)
    if sort=='price_low': books=books.order_by('price','id')
    elif sort=='price_high': books=books.order_by('-price','id')
    else: books=books.order_by('-created_at','-id')
    total_count=books.count()
    if q and total_count == 0:
        Event.objects.create(user=request.user if request.user.is_authenticated else None,name='search_zero_result',metadata={'query':q})
        tokens=[t for t in q.split() if len(t)>1]
        relaxed=Q()
        for token in tokens:
            relaxed |= Q(name__icontains=token)|Q(author__name__icontains=token)|Q(summary__icontains=token)
        if relaxed:
            books=_published_books().select_related('author','category').filter(relaxed).order_by('-created_at','-id')
            total_count=books.count()
    page_obj=Paginator(books,24).get_page(request.GET.get('page'))
    return render(request,'books/list.html',{'books':page_obj.object_list,'page_obj':page_obj,'total_count':total_count,'q':q,'cat':cat,'sort':sort,'kind':kind,'price':price,'categories':Category.objects.all()})

def detail(request,slug):
    book=get_object_or_404(_published_books().select_related('author','category','level').prefetch_related('chapters'),slug=slug)
    approved_reviews=book.review_set.filter(approved=True).select_related('user').order_by('-created_at')[:8]
    review_stats=book.review_set.filter(approved=True).aggregate(avg=Avg('rating'),count=Count('id'))
    related=_published_books().filter(category=book.category).exclude(pk=book.pk)[:4] if book.category else Book.objects.none()
    has_access = request.user.is_authenticated and (book.visibility == 'public' or Entitlement.objects.filter(user=request.user,book=book).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).exists())
    return render(request,'books/detail.html',{'book':book,'related':related,'has_access':has_access,'review_avg':review_stats['avg'],'review_count':review_stats['count'],'approved_reviews':approved_reviews})


def secure_file(request, pk, kind, chapter_id=None):
    book = get_object_or_404(_published_books(), pk=pk)
    if not request.user.is_authenticated:
        return HttpResponseForbidden('ورود لازم است.')
    if book.visibility != 'public' and not Entitlement.objects.filter(user=request.user, book=book).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).exists():
        return HttpResponseForbidden('دسترسی به این فایل ندارید.')
    if kind == 'chapter_audio':
        chapter = book.chapters.filter(pk=chapter_id).first()
        field = chapter.audio if chapter else None
    else:
        field = {'pdf': book.pdf, 'audio': book.audio}.get(kind)
    if not field:
        return HttpResponseForbidden('فایل موجود نیست.')
    response = FileResponse(field.open('rb'), content_type='application/pdf' if kind == 'pdf' else 'audio/mpeg')
    response['Content-Disposition'] = f'inline; filename="{field.name.rsplit("/", 1)[-1]}"'
    return response

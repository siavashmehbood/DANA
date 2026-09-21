from django.shortcuts import render,get_object_or_404
from django.db.models import Q
from django.http import FileResponse, HttpResponseForbidden
from django.urls import reverse
from django.utils import timezone
from shop.models import Entitlement
from .models import Book,Category

def _published_books():
    return Book.objects.filter(Q(status='published') | Q(status='scheduled', publish_at__lte=timezone.now()))

def listing(request):
    q=request.GET.get('q','').strip()[:200]; cat=request.GET.get('cat','').strip(); sort=request.GET.get('sort','new')
    books=_published_books().select_related('author','category')
    if q:
        normalized=q.replace('ي','ی').replace('ك','ک').replace('\u200c',' ')
        books=books.filter(Q(name__icontains=normalized)|Q(author__name__icontains=normalized)|Q(summary__icontains=normalized)|Q(description__icontains=normalized))
    if cat: books=books.filter(category__slug=cat)
    if sort=='price_low': books=books.order_by('price')
    elif sort=='price_high': books=books.order_by('-price')
    else: books=books.order_by('-created_at')
    return render(request,'books/list.html',{'books':books,'q':q,'cat':cat,'sort':sort,'categories':Category.objects.all()})

def detail(request,slug):
    book=get_object_or_404(_published_books().select_related('author','category','level').prefetch_related('chapters'),slug=slug)
    related=_published_books().filter(category=book.category).exclude(pk=book.pk)[:4] if book.category else Book.objects.none()
    has_access = request.user.is_authenticated and (book.visibility == 'public' or Entitlement.objects.filter(user=request.user,book=book).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).exists())
    return render(request,'books/detail.html',{'book':book,'related':related,'has_access':has_access})


def secure_file(request, pk, kind):
    book = get_object_or_404(_published_books(), pk=pk)
    if not request.user.is_authenticated:
        return HttpResponseForbidden('ورود لازم است.')
    if book.visibility != 'public' and not Entitlement.objects.filter(user=request.user, book=book).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).exists():
        return HttpResponseForbidden('دسترسی به این فایل ندارید.')
    field = {'pdf': book.pdf, 'audio': book.audio}.get(kind)
    if not field:
        return HttpResponseForbidden('فایل موجود نیست.')
    response = FileResponse(field.open('rb'), content_type='application/pdf' if kind == 'pdf' else 'audio/mpeg')
    response['Content-Disposition'] = f'inline; filename="{field.name.rsplit("/", 1)[-1]}"'
    return response

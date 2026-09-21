from django.shortcuts import render,get_object_or_404
from django.db.models import Q
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.http import FileResponse, HttpResponseForbidden
from django.urls import reverse
from django.utils import timezone
from shop.models import Entitlement
from .models import Book,Category

def _published_books():
    return Book.objects.filter(Q(status='published') | Q(status='scheduled', publish_at__lte=timezone.now()))

def listing(request):
    q=request.GET.get('q','').strip(); cat=request.GET.get('cat','').strip(); sort=request.GET.get('sort','new')
    books=_published_books().select_related('author','category')
    if q: books=books.filter(Q(name__icontains=q)|Q(author__name__icontains=q)|Q(summary__icontains=q)|Q(description__icontains=q))
    if cat: books=books.filter(category__slug=cat)
    if sort=='price_low': books=books.order_by('price')
    elif sort=='price_high': books=books.order_by('-price')
    else: books=books.order_by('-created_at')
    return render(request,'books/list.html',{'books':books,'q':q,'cat':cat,'sort':sort,'categories':Category.objects.all()})

def detail(request,slug):
    book=get_object_or_404(_published_books().select_related('author','category','level').prefetch_related('chapters'),slug=slug)
    related=_published_books().filter(category=book.category).exclude(pk=book.pk)[:4] if book.category else Book.objects.none()
    return render(request,'books/detail.html',{'book':book,'related':related})


def secure_file(request, pk, kind):
    book = get_object_or_404(_published_books(), pk=pk)
    if not request.user.is_authenticated:
        return HttpResponseForbidden('ورود لازم است.')
    if book.visibility != 'public' and not Entitlement.objects.filter(user=request.user, book=book).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).exists():
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
    return response

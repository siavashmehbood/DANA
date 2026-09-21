from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from books.models import Book, Category
from articles.models import Article, ArticleCategory
from shop.models import Entitlement
from reader.models import ReadingProgress
from django.db.models import Q
from django.utils import timezone


def home(request):
    base = Book.objects.filter(Q(status='published') | Q(status='scheduled', publish_at__lte=timezone.now())).select_related('author', 'category')
    featured = base.order_by('-created_at')[:6]
    newest = base.order_by('-created_at')[:8]
    popular = base.order_by('-id')[:8]
    audio_books = base.filter(Q(audio__gt='')|Q(chapters__audio__gt='')).distinct().order_by('-created_at')[:8]
    categories = Category.objects.all()[:10]
    readable = Q(full_text__gt='') | Q(full_text_fa__gt='') | Q(abstract__gt='') | Q(abstract_fa__gt='') | Q(pdf_url__gt='') | Q(pdf__gt='')
    article_base = Article.objects.filter(published=True).filter(readable).select_related('category')
    continue_reading=[]
    if request.user.is_authenticated:
        valid_books=Entitlement.objects.filter(user=request.user).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).values_list('book_id',flat=True)
        continue_reading=ReadingProgress.objects.filter(user=request.user,book_id__in=valid_books,progress__gt=0,progress__lt=100).select_related('book__author').order_by('-updated_at')[:6]
    return render(request, 'home.html', {'featured': featured, 'newest': newest, 'popular': popular, 'categories': categories,
        'latest_articles': article_base.order_by('-created_at')[:8], 'featured_articles': article_base.filter(featured=True)[:4],
        'article_categories': ArticleCategory.objects.filter(is_active=True)[:8], 'article_count': article_base.count(), 'continue_reading': continue_reading, 'audio_books': audio_books})


def admin_logout(request):
    logout(request)
    return redirect('/admin/login/')


@login_required
def protected_book_pdf(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if book.visibility != 'public' and not Entitlement.objects.filter(user=request.user, book=book).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).exists():
        return HttpResponse('Access denied', status=403)
    if not book.pdf or not book.is_published:
        raise Http404
    response = FileResponse(book.pdf.open('rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="book-{book.pk}.pdf"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def pwa_manifest(request):
    return JsonResponse({'name': 'دانا | کتابخانه هوشمند', 'short_name': 'دانا', 'lang': 'fa', 'dir': 'rtl', 'start_url': '/', 'scope': '/', 'display': 'standalone', 'background_color': '#0b1020', 'theme_color': '#0b1020', 'icons': [{'src': '/static/img/icon.svg', 'sizes': 'any', 'type': 'image/svg+xml', 'purpose': 'any maskable'}]})


def service_worker(request):
    js = """const CACHE='dana-v3'; const CORE=['/','/books/','/articles/'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{if(event.request.method!=='GET')return;event.respondWith(fetch(event.request).then(response=>{if(response.ok&&new URL(event.request.url).origin===location.origin){const copy=response.clone();caches.open(CACHE).then(c=>c.put(event.request,copy));}return response;}).catch(()=>caches.match(event.request).then(r=>r||caches.match('/'))));});"""
    return HttpResponse(js, content_type='application/javascript')

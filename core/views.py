from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.utils.html import escape
from django.shortcuts import render, redirect, get_object_or_404
from books.models import Book, Category
from articles.models import Article, ArticleCategory
from shop.models import Entitlement, Subscription
from reader.models import ReadingProgress, AudioProgress, Review
from django.db.models import Q, Count
from django.utils import timezone


def home(request):
    base = Book.objects.filter(Q(status='published') | Q(status='scheduled', publish_at__lte=timezone.now()),visibility='public').select_related('author', 'category')
    featured = base.filter(featured=True).order_by('-created_at')[:6]
    if not featured.exists():
        featured = base.order_by('-created_at')[:6]
    newest = base.order_by('-created_at')[:8]
    popular = base.annotate(approved_reviews=Count('review', filter=Q(review__approved=True))).order_by('-approved_reviews','-created_at')[:8]
    recommendations = base.none()
    audio_books = base.filter(Q(audio__gt='')|Q(chapters__audio__gt='')).distinct().order_by('-created_at')[:8]
    public_book_filter=(Q(book__status='published')|Q(book__status='scheduled',book__publish_at__lte=timezone.now())) & Q(book__visibility='public')
    categories = Category.objects.annotate(book_count=Count('book',filter=public_book_filter)).filter(book_count__gt=0).order_by('-book_count','name')[:10]
    readable = Q(full_text__gt='') | Q(full_text_fa__gt='') | Q(abstract__gt='') | Q(abstract_fa__gt='') | Q(pdf_url__gt='') | Q(pdf__gt='')
    article_base = Article.objects.filter(published=True).filter(readable).select_related('category')
    continue_reading=[]
    continue_listening=[]
    continue_item=None
    if request.user.is_authenticated:
        valid_books=Entitlement.objects.filter(user=request.user).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).values_list('book_id',flat=True)
        subscription_access=Subscription.objects.filter(user=request.user,status='active',starts_at__lte=timezone.now(),expires_at__gt=timezone.now(),plan__grants_catalog_access=True).exists()
        readable_progress=Q(book_id__in=valid_books)|Q(book__visibility='public',book__price=0)
        if subscription_access:
            readable_progress |= Q(book__subscription_included=True)
        continue_reading=ReadingProgress.objects.filter(readable_progress,user=request.user,progress__gt=0,progress__lt=100).filter(Q(book__status='published')|Q(book__status='scheduled',book__publish_at__lte=timezone.now())).select_related('book__author').order_by('-updated_at')[:6]
        continue_listening=AudioProgress.objects.filter(readable_progress,user=request.user,position_seconds__gt=0,completed=False).filter(Q(book__status='published')|Q(book__status='scheduled',book__publish_at__lte=timezone.now())).select_related('book__author','chapter').order_by('-updated_at')[:6]
        latest_reading=continue_reading[0] if continue_reading else None
        latest_listening=continue_listening[0] if continue_listening else None
        if latest_listening and (not latest_reading or latest_listening.updated_at > latest_reading.updated_at):
            continue_item={'book':latest_listening.book,'kind':'audio'}
        elif latest_reading:
            continue_item={'book':latest_reading.book,'kind':'text'}
        owned_categories=Entitlement.objects.filter(user=request.user,book__category__isnull=False).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).values_list('book__category_id',flat=True)
        owned_ids=set(Entitlement.objects.filter(user=request.user).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).values_list('book_id',flat=True))
        # Subscription access is not ownership. Keep unengaged catalog titles
        # eligible for recommendations while excluding anything already started.
        owned_ids.update(ReadingProgress.objects.filter(user=request.user).values_list('book_id',flat=True))
        owned_ids.update(AudioProgress.objects.filter(user=request.user).values_list('book_id',flat=True))
        rated_categories=Review.objects.filter(user=request.user,approved=True,rating__gte=4,book__category__isnull=False).values_list('book__category_id',flat=True)
        active_categories=ReadingProgress.objects.filter(user=request.user,progress__gt=0,book__category__isnull=False).values_list('book__category_id',flat=True)
        completed_categories=ReadingProgress.objects.filter(user=request.user,progress__gte=100,book__category__isnull=False).values_list('book__category_id',flat=True)
        recent_category_ids=list(ReadingProgress.objects.filter(user=request.user,book__category__isnull=False).order_by('-updated_at').values_list('book__category_id',flat=True)[:12])
        preferred_categories=set(owned_categories)|set(rated_categories)|set(active_categories)|set(completed_categories)|set(recent_category_ids)
        recommendations=base.filter(category_id__in=preferred_categories).exclude(id__in=owned_ids).annotate(approved_reviews=Count('review',filter=Q(review__approved=True))).order_by('-approved_reviews','-created_at').distinct()[:8]
        if not recommendations.exists():
            recommendations=base.exclude(id__in=owned_ids).annotate(approved_reviews=Count('review',filter=Q(review__approved=True))).order_by('-approved_reviews','-created_at')[:8]
    response=render(request, 'home.html', {'featured': featured, 'newest': newest, 'popular': popular, 'categories': categories,
        'latest_articles': article_base.order_by('-created_at')[:8], 'featured_articles': article_base.filter(featured=True)[:4],
        'article_categories': ArticleCategory.objects.filter(is_active=True)[:8], 'article_count': article_base.count(), 'continue_reading': continue_reading, 'continue_listening':continue_listening, 'continue_item':continue_item, 'audio_books': audio_books, 'recommendations': recommendations})
    if request.user.is_authenticated:
        response['Cache-Control']='private, no-store'
        response['Vary']='Cookie'
    return response


def admin_logout(request):
    logout(request)
    return redirect('/admin/login/')


@login_required
def protected_book_pdf(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if not book.is_published:
        raise Http404
    free_public = book.visibility == 'public' and book.price == 0
    if not free_public:
        entitled=Entitlement.objects.filter(user=request.user, book=book).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).exists()
        subscribed=book.subscription_included and Subscription.objects.filter(user=request.user,status='active',starts_at__lte=timezone.now(),expires_at__gt=timezone.now(),plan__grants_catalog_access=True).exists()
        if not entitled and not subscribed:
            return HttpResponse('Access denied', status=403)
    if not book.pdf:
        raise Http404
    if book.visibility == 'password':
        return HttpResponse('Password-protected books must be opened through the reader.', status=403)
    if book.pdf.name and not book.pdf.name.lower().endswith('.pdf'):
        raise Http404
    try:
        size=book.pdf.size
    except (OSError,ValueError):
        raise Http404
    response = FileResponse(book.pdf.open('rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="book-{book.pk}.pdf"'
    response['Accept-Ranges'] = 'none'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'self'; sandbox"
    response['Cache-Control'] = 'private, no-store'
    response['Referrer-Policy'] = 'same-origin'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    response['Content-Length'] = str(size)
    return response


def pwa_manifest(request):
    response=JsonResponse({'name': 'دانا | کتابخانه هوشمند', 'short_name': 'دانا', 'lang': 'fa', 'dir': 'rtl', 'start_url': '/', 'scope': '/', 'display': 'standalone', 'background_color': '#0b1020', 'theme_color': '#0b1020', 'icons': [{'src': '/static/img/icon.svg', 'sizes': 'any', 'type': 'image/svg+xml', 'purpose': 'any maskable'}]})
    response['Cache-Control']='public, max-age=3600'
    response['X-Content-Type-Options']='nosniff'
    return response


def service_worker(request):
    js = """const CACHE='dana-v6'; const CORE=[];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{if(event.request.method!=='GET')return;const url=new URL(event.request.url);const cacheable=url.origin===location.origin&&(url.pathname.startsWith('/static/')||CORE.includes(url.pathname));if(!cacheable)return;event.respondWith(fetch(event.request,{credentials:'same-origin'}).then(response=>{if(response.ok&&response.type==='basic'&&!response.headers.get('Cache-Control')?.includes('private')){const copy=response.clone();caches.open(CACHE).then(c=>c.put(event.request,copy));}return response;}).catch(()=>caches.match(event.request)));});"""
    response=HttpResponse(js, content_type='application/javascript')
    response['Cache-Control']='no-cache'
    response['Service-Worker-Allowed']='/'
    response['X-Content-Type-Options']='nosniff'
    return response


def robots_txt(request):
    body = "User-agent: *\nDisallow: /admin/\nDisallow: /protected/\nDisallow: /reader/\nSitemap: " + request.build_absolute_uri('/sitemap.xml') + "\n"
    response=HttpResponse(body, content_type='text/plain')
    response['Cache-Control']='public, max-age=3600'
    response['X-Content-Type-Options']='nosniff'
    return response


def sitemap_xml(request):
    base=request.build_absolute_uri('/').rstrip('/')
    urls=[base+'/',base+'/books/',base+'/articles/',base+'/shop/subscriptions/']
    urls += [base+'/books/'+slug+'/' for slug in Book.objects.filter(Q(status='published')|Q(status='scheduled',publish_at__lte=timezone.now()),visibility='public').values_list('slug',flat=True)[:5000]]
    readable = Q(full_text__gt='') | Q(full_text_fa__gt='') | Q(abstract__gt='') | Q(abstract_fa__gt='') | Q(pdf_url__gt='') | Q(pdf__gt='')
    urls += [base+'/articles/'+slug+'/' for slug in Article.objects.filter(published=True).filter(readable).values_list('slug',flat=True)[:5000]]
    urls=list(dict.fromkeys(urls))
    body='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{escape(url)}</loc></url>' for url in urls) + '</urlset>'
    response=HttpResponse(body, content_type='application/xml')
    response['Cache-Control']='public, max-age=900'
    response['X-Content-Type-Options']='nosniff'
    return response

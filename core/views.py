from django.contrib.auth import logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from books.models import Book, Category
from articles.models import Article, ArticleCategory


def home(request):
    base = Book.objects.filter(status__in=['published', 'scheduled']).select_related('author', 'category')
    featured = base.order_by('-created_at')[:6]
    newest = base.order_by('-created_at')[:8]
    popular = base.order_by('-id')[:8]
    categories = Category.objects.all()[:10]
    article_base = Article.objects.filter(published=True).select_related('category')
    latest_articles = article_base.order_by('-created_at')[:8]
    featured_articles = article_base.filter(featured=True)[:4]
    article_categories = ArticleCategory.objects.filter(is_active=True)[:8]
    return render(request, 'home.html', {
        'featured': featured,
        'newest': newest,
        'popular': popular,
        'categories': categories,
        'latest_articles': latest_articles,
        'featured_articles': featured_articles,
        'article_categories': article_categories,
        'article_count': article_base.count(),
    })


def admin_logout(request):
    logout(request)
    return redirect('/admin/login/')


def pwa_manifest(request):
    return JsonResponse({'name': 'دانا | کتابخانه هوشمند', 'short_name': 'دانا', 'lang': 'fa', 'dir': 'rtl', 'start_url': '/', 'scope': '/', 'display': 'standalone', 'background_color': '#0b1020', 'theme_color': '#0b1020', 'icons': []})


def service_worker(request):
    js = """const CACHE='dana-v1';
const CORE=['/','/books/','/articles/'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET') return;
  event.respondWith(fetch(event.request).then(response=>{
    const copy=response.clone(); caches.open(CACHE).then(c=>c.put(event.request,copy)); return response;
  }).catch(()=>caches.match(event.request).then(r=>r || caches.match('/'))));
});
"""
    return HttpResponse(js, content_type='application/javascript')

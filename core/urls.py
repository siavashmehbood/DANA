from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import home, admin_logout, pwa_manifest, service_worker

urlpatterns = [
    path('admin/logout/', admin_logout, name='admin_logout'),
    path('admin/', admin.site.urls),
    path('manifest.json', pwa_manifest, name='pwa_manifest'),
    path('sw.js', service_worker, name='service_worker'),
    path('', home, name='home'),
    path('', include('accounts.urls')),
    path('books/', include('books.urls')),
    path('articles/', include('articles.urls')),
    path('shop/', include('shop.urls')),
    path('reader/', include('reader.urls')),
    path('gamification/', include('gamification.urls')),
    path('analytics/', include('analytics.urls')),
    path('notifications/', include('notifications.urls')),
    path('support/', include('support.urls')),
    path('api/', include('api.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

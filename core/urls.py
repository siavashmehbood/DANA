from django.contrib import admin
from django.urls import path, include
from .views import home, admin_logout, pwa_manifest, service_worker, protected_book_pdf
from . import admin as dana_admin  # noqa: F401  # Load DANA admin dashboard/localization.

urlpatterns = [
    path('admin/logout/', admin_logout, name='admin_logout'),
    path('admin/', admin.site.urls),
    path('manifest.json', pwa_manifest, name='pwa_manifest'),
    path('sw.js', service_worker, name='service_worker'),
    path('protected/books/<int:pk>/pdf/', protected_book_pdf, name='protected_book_pdf'),
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
]

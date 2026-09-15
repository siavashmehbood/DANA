# -*- coding: utf-8 -*-
from datetime import timedelta

from django.contrib import admin
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from accounts.models import User
from articles.models import Article
from books.models import Book
from shop.models import Order, OrderItem, WalletTransaction


ADMIN_LABELS = {
    'accounts': 'حساب‌های کاربری',
    'analytics': 'تحلیل و آمار',
    'articles': 'مقالات',
    'books': 'کتاب‌ها',
    'gamification': 'بازی‌وارسازی',
    'notifications': 'اعلان‌ها',
    'reader': 'مطالعه',
    'shop': 'فروشگاه',
    'support': 'پشتیبانی',
    'api': 'رابط برنامه‌نویسی',
    'devices': 'دستگاه‌ها',
    'otp codes': 'کدهای ورود',
    'user sessions': 'نشست‌های کاربران',
    'events': 'رویدادها',
    'article categories': 'دسته‌های مقالات',
    'authors': 'نویسندگان',
    'books': 'کتاب‌ها',
    'categorys': 'دسته‌بندی‌ها',
    'chapters': 'فصل‌ها',
    'levels': 'سطح‌ها',
    'media assets': 'فایل‌های رسانه‌ای',
    'badges': 'نشان‌ها',
    'missions': 'مأموریت‌ها',
    'orders': 'سفارش‌ها',
    'order items': 'اقلام سفارش',
    'wallet transactions': 'تراکنش‌های کیف پول',
    'tickets': 'تیکت‌ها',
    'ticket messages': 'پیام‌های تیکت',
    'reading progresss': 'پیشرفت مطالعه',
    'reviews': 'دیدگاه‌ها',
}


def _persianize_app_list(app_list):
    for app in app_list:
        app['name'] = ADMIN_LABELS.get(app['name'].lower(), app['name'])
        for model in app.get('models', []):
            model['name'] = ADMIN_LABELS.get(model['name'].lower(), model['name'])
    return app_list


def dana_dashboard_stats():
    now = timezone.now()
    paid = Order.objects.filter(status__in=['paid', 'gift'])
    today = paid.filter(created_at__date=now.date())
    wallet = WalletTransaction.objects.filter(type='credit').aggregate(
        total=Sum('amount')
    )['total'] or 0
    return {
        'users': User.objects.filter(is_active=True, is_deactivated=False).count(),
        'books': Book.objects.filter(status='published').count(),
        'articles': Article.objects.filter(published=True).count(),
        'translated_articles': Article.objects.filter(published=True).exclude(title_fa='').count(),
        'fulltext_articles': Article.objects.filter(published=True).exclude(full_text_fa='').count(),
        'pdf_articles': Article.objects.filter(published=True).exclude(pdf='').count(),
        'orders': paid.count(),
        'revenue': paid.aggregate(total=Sum('total'))['total'] or 0,
        'today_revenue': today.aggregate(total=Sum('total'))['total'] or 0,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'wallet': wallet,
    }


def _dana_index(request, extra_context=None):
    context = admin.site.each_context(request)
    context.update(extra_context or {})
    context['title'] = 'مدیریت وب‌گاه'
    context['dana_stats'] = dana_dashboard_stats()
    context['app_list'] = _persianize_app_list(admin.site.get_app_list(request))
    return render(request, 'admin/index.html', context)


admin.site.index = _dana_index

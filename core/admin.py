# -*- coding: utf-8 -*-
from django.contrib import admin
from django.db.models import Sum, Q, Count
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from articles.models import Article
from books.models import Book
from shop.models import Order, Payment, WalletTransaction
from support.models import Ticket


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
}


def _persianize_app_list(app_list):
    for app in app_list:
        app['name'] = ADMIN_LABELS.get(app['app_url'].rstrip('/').split('/')[-1], app['name'])
        for model in app.get('models', []):
            # model verbose_name is already localized by core.admin_labels.
            model['name'] = str(model['name'])
    return app_list


def dana_dashboard_stats():
    now = timezone.now()
    paid = Order.objects.filter(status__in=['paid', 'gift'])
    order_totals=paid.aggregate(orders=Count('id'),revenue=Sum('total'),today_revenue=Sum('total',filter=Q(created_at__date=now.date())),week_revenue=Sum('total',filter=Q(created_at__gte=now-timezone.timedelta(days=7))))
    payment_totals=Payment.objects.aggregate(pending=Count('id',filter=Q(status='pending')),failed=Count('id',filter=Q(status='failed')))
    wallet = WalletTransaction.objects.filter(type='credit').aggregate(total=Sum('amount'))['total'] or 0
    pending_payments = payment_totals['pending']
    failed_payments = payment_totals['failed']
    open_tickets = Ticket.objects.exclude(status__in=['resolved', 'closed']).count()
    translation_backlog = Article.objects.filter(published=True).filter(Q(translation_status__in=['not_requested','pending','translating','failed','provider_failed','validation_failed','retry_pending']) | Q(title_fa='') | Q(abstract__gt='', abstract_fa='') | (Q(full_text__gt='', full_text_fa='') & (Q(source__isnull=True) | Q(source__allow_full_republish=True)))).distinct().count()
    translation_failures = Article.objects.filter(published=True, translation_status__in=['failed','provider_failed','validation_failed']).count()
    return {
        'users': User.objects.filter(is_active=True, is_deactivated=False).count(),
        'books': Book.objects.filter(status='published').count(),
        'articles': Article.objects.filter(published=True).count(),
        'translated_articles': Article.objects.filter(published=True).exclude(title_fa='').count(),
        'fulltext_articles': Article.objects.filter(published=True).exclude(full_text_fa='').count(),
        'pdf_articles': Article.objects.filter(published=True).exclude(pdf='').count(),
        'orders': order_totals['orders'],
        'revenue': order_totals['revenue'] or 0,
        'today_revenue': order_totals['today_revenue'] or 0,
        'week_revenue': order_totals['week_revenue'] or 0,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_payments': pending_payments,
        'failed_payments': failed_payments,
        'open_tickets': open_tickets,
        'translation_backlog': translation_backlog,
        'translation_failures': translation_failures,
        'wallet': wallet,
    }


def _quick_link(label, url_name, icon):
    return {'label': label, 'url': reverse(url_name), 'icon': icon}


def _dana_index(request, extra_context=None):
    context = admin.site.each_context(request)
    context.update(extra_context or {})
    stats = dana_dashboard_stats()

    recent_orders = []
    for order in Order.objects.select_related('user').order_by('-created_at')[:6]:
        recent_orders.append({
            'code': order.tracking_code,
            'user': order.user.get_full_name() or order.user.phone or order.user.username,
            'total': order.total,
            'status': order.get_status_display(),
            'status_key': order.status,
            'created_at': order.created_at,
            'url': reverse('admin:shop_order_change', args=[order.pk]),
        })

    attention = [
        {'label': 'پرداخت‌های در انتظار', 'count': stats['pending_payments'], 'url': reverse('admin:shop_payment_changelist'), 'tone': 'warning'},
        {'label': 'پرداخت‌های ناموفق', 'count': stats['failed_payments'], 'url': reverse('admin:shop_payment_changelist'), 'tone': 'danger'},
        {'label': 'سفارش‌های در انتظار', 'count': stats['pending_orders'], 'url': reverse('admin:shop_order_changelist'), 'tone': 'warning'},
        {'label': 'تیکت‌های باز', 'count': stats['open_tickets'], 'url': reverse('admin:support_ticket_changelist'), 'tone': 'info'},
        {'label': 'صف ترجمه مقالات', 'count': stats['translation_backlog'], 'url': reverse('admin:articles_article_changelist') + '?translation_health=backlog', 'tone': 'warning'},
        {'label': 'خطاهای ترجمه', 'count': stats['translation_failures'], 'url': reverse('admin:articles_article_changelist') + '?translation_health=backlog', 'tone': 'danger'},
    ]

    context.update({
        'title': 'داشبورد مدیریت دانا',
        'dana_stats': stats,
        'recent_orders': recent_orders,
        'attention': attention,
        'quick_links': [
            _quick_link('افزودن کتاب', 'admin:books_book_add', '📚'),
            _quick_link('افزودن مقاله', 'admin:articles_article_add', '📝'),
            _quick_link('مشاهده سفارش‌ها', 'admin:shop_order_changelist', '🛒'),
            _quick_link('مدیریت پرداخت‌ها', 'admin:shop_payment_changelist', '💳'),
            _quick_link('کاربران', 'admin:accounts_user_changelist', '👥'),
            _quick_link('تیکت‌های پشتیبانی', 'admin:support_ticket_changelist', '🎧'),
        ],
        'app_list': _persianize_app_list(admin.site.get_app_list(request)),
    })
    return render(request, 'admin/index.html', context)


admin.site.index = _dana_index

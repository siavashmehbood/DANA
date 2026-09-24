# -*- coding: utf-8 -*-
from django.contrib import admin
from django.db.models import Sum
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.core.signals import request_started

from core import admin_labels  # noqa: F401


def _apply_persian_admin_labels(*args, **kwargs):
    from core.admin_labels import MODEL_LABELS, FIELD_LABELS, CHOICE_LABELS
    for model_class in admin.site._registry:
        label = MODEL_LABELS.get(model_class.__name__)
        if label:
            singular = label[:-3] if label.endswith('‌ها') else label[:-2] if label.endswith('ها') else label
            model_class._meta.verbose_name = singular
            model_class._meta.verbose_name_plural = label
        for field in model_class._meta.fields:
            if field.name in FIELD_LABELS:
                field.verbose_name = FIELD_LABELS[field.name]
            if getattr(field, 'choices', None):
                field.choices = [(v, CHOICE_LABELS.get(str(v), lbl)) for v, lbl in field.choices]


request_started.connect(_apply_persian_admin_labels, dispatch_uid='dana-admin-persian-labels')

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
    from core.admin_labels import MODEL_LABELS, SINGULAR_LABELS, FIELD_LABELS, CHOICE_LABELS
    registered = {m._meta.model_name: m for m in admin.site._registry}
    for app in app_list:
        app['name'] = ADMIN_LABELS.get(app['app_url'].rstrip('/').split('/')[-1], app['name'])
        for model in app.get('models', []):
            model_name = model.get('admin_url', '').rstrip('/').split('/')[-1]
            model_class = next((m for m in admin.site._registry if m._meta.model_name == model_name), None)
            if model_class:
                label = MODEL_LABELS.get(model_class.__name__)
                if label:
                    model_class._meta.verbose_name = SINGULAR_LABELS.get(model_class.__name__, label)
                    model_class._meta.verbose_name_plural = label
                for field in model_class._meta.fields:
                    if field.name in FIELD_LABELS:
                        field.verbose_name = FIELD_LABELS[field.name]
                    if getattr(field, 'choices', None):
                        field.choices = [(v, CHOICE_LABELS.get(str(v), lbl)) for v, lbl in field.choices]
                model['name'] = model_class._meta.verbose_name_plural
    return app_list


def dana_dashboard_stats():
    now = timezone.now()
    paid = Order.objects.filter(status__in=['paid', 'gift'])
    today = paid.filter(created_at__date=now.date())
    week = paid.filter(created_at__gte=now - timezone.timedelta(days=7))
    wallet = WalletTransaction.objects.filter(type='credit').aggregate(total=Sum('amount'))['total'] or 0
    pending_payments = Payment.objects.filter(status='pending').count()
    failed_payments = Payment.objects.filter(status='failed').count()
    open_tickets = Ticket.objects.exclude(status__in=['resolved', 'closed']).count()
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
        'week_revenue': week.aggregate(total=Sum('total'))['total'] or 0,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_payments': pending_payments,
        'failed_payments': failed_payments,
        'open_tickets': open_tickets,
        'wallet': wallet,
    }


def _quick_link(label, url_name, icon):
    return {'label': label, 'url': reverse(url_name), 'icon': icon}


def _dana_index(request, extra_context=None):
    from core.admin_labels import MODEL_LABELS, FIELD_LABELS, CHOICE_LABELS
    for model_class in admin.site._registry:
        label = MODEL_LABELS.get(model_class.__name__)
        if label:
            singular = label[:-3] if label.endswith('‌ها') else label[:-2] if label.endswith('ها') else label
            model_class._meta.verbose_name = singular
            model_class._meta.verbose_name_plural = label
        for field in model_class._meta.fields:
            if field.name in FIELD_LABELS:
                field.verbose_name = FIELD_LABELS[field.name]
            if getattr(field, 'choices', None):
                field.choices = [(v, CHOICE_LABELS.get(str(v), lbl)) for v, lbl in field.choices]

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

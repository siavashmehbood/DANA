# -*- coding: utf-8 -*-
from django.apps import apps

APP_LABELS = {
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

MODEL_LABELS = {
    'Device': 'دستگاه‌ها',
    'OTPCode': 'کدهای یکبارمصرف',
    'UserSession': 'نشست‌های کاربران',
    'User': 'کاربران',
    'Author': 'نویسندگان',
    'Book': 'کتاب‌ها',
    'Category': 'دسته‌بندی‌ها',
    'Chapter': 'فصل‌ها',
    'Level': 'سطح‌ها',
    'MediaAsset': 'رسانه‌ها',
    'Badge': 'نشان‌ها',
    'GamificationLevel': 'سطح‌های بازی‌وارسازی',
    'HallOfFameRecord': 'تالار افتخار',
    'Mission': 'مأموریت‌ها',
    'PointLedger': 'دفتر امتیازها',
    'UserBadge': 'نشان‌های کاربران',
    'UserMission': 'مأموریت‌های کاربران',
    'UserStreak': 'تداوم فعالیت کاربران',
    'XPEvent': 'رویدادهای XP',
    'Order': 'سفارش‌ها',
    'OrderItem': 'اقلام سفارش',
    'Coupon': 'کدهای تخفیف',
    'Entitlement': 'دسترسی کتاب‌ها',
    'Referral': 'معرفی دوستان',
    'WalletTransaction': 'تراکنش‌های کیف پول',
    'Ticket': 'تیکت‌ها',
    'TicketMessage': 'پیام‌های تیکت',
    'Review': 'نقد و بررسی‌ها',
    'ReadingProgress': 'پیشرفت مطالعه',
    'Bookmark': 'نشانک‌ها',
    'Note': 'یادداشت‌ها',
    'ProblemReport': 'گزارش مشکلات',
    'Notification': 'اعلان‌ها',
    'EmailLog': 'گزارش‌های ایمیل',
    'PushSubscription': 'اشتراک‌های اعلان فوری',
    'Event': 'رویدادها',
}

for app_config in apps.get_app_configs():
    if app_config.label in APP_LABELS:
        app_config.verbose_name = APP_LABELS[app_config.label]

for model in apps.get_models():
    label = MODEL_LABELS.get(model.__name__)
    if label:
        model._meta.verbose_name = label
        model._meta.verbose_name_plural = label

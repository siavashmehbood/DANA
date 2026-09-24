"""Runtime-only Persian labels for the Django admin.

These labels intentionally do not alter database field names, migrations, or API
contracts.  Django admin reads model metadata at runtime, so this keeps the
management UI Persian without creating schema-only migrations.
"""
import sys
from django.apps import apps

APP_LABELS = {
    'accounts': 'کاربران و حساب‌ها', 'books': 'کتاب‌ها و محتوا', 'shop': 'فروش و اشتراک',
    'reader': 'مطالعه و یادداشت‌ها', 'gamification': 'بازی‌وارسازی', 'analytics': 'تحلیل و رویدادها',
    'notifications': 'اعلان‌ها', 'support': 'پشتیبانی', 'articles': 'مقالات',
    'api': 'رابط برنامه‌نویسی', 'core': 'هسته سامانه',
}
MODEL_LABELS = {
    'User': ('کاربر','کاربران'), 'Device': ('دستگاه','دستگاه‌ها'), 'OTPCode': ('کد یک‌بارمصرف','کدهای یک‌بارمصرف'), 'UserSession': ('نشست کاربر','نشست‌های کاربران'),
    'Author': ('نویسنده','نویسندگان'), 'Category': ('دسته‌بندی کتاب','دسته‌بندی‌های کتاب'), 'Level': ('سطح کتاب','سطوح کتاب'), 'Book': ('کتاب','کتاب‌ها'), 'Chapter': ('فصل','فصل‌ها'), 'MediaAsset': ('رسانه','رسانه‌ها'),
    'Coupon': ('کد تخفیف','کدهای تخفیف'), 'CartItem': ('آیتم سبد','آیتم‌های سبد'), 'Order': ('سفارش','سفارش‌ها'), 'OrderItem': ('آیتم سفارش','آیتم‌های سفارش'), 'Entitlement': ('مجوز دسترسی','مجوزهای دسترسی'), 'WalletTransaction': ('تراکنش کیف پول','تراکنش‌های کیف پول'), 'CheckoutRequest': ('درخواست تسویه','درخواست‌های تسویه'), 'Payment': ('پرداخت','پرداخت‌ها'), 'Referral': ('دعوت','دعوت‌ها'), 'SubscriptionPlan': ('طرح اشتراک','طرح‌های اشتراک'), 'Subscription': ('اشتراک','اشتراک‌ها'),
    'ReadingProgress': ('پیشرفت مطالعه','پیشرفت‌های مطالعه'), 'ReadingActivity': ('فعالیت مطالعه','فعالیت‌های مطالعه'), 'ListeningActivity': ('فعالیت شنیدن','فعالیت‌های شنیدن'), 'AudioProgress': ('پیشرفت صوتی','پیشرفت‌های صوتی'), 'Bookmark': ('نشانک','نشانک‌ها'), 'Highlight': ('هایلایت','هایلایت‌ها'), 'Note': ('یادداشت','یادداشت‌ها'), 'ProblemReport': ('گزارش مشکل','گزارش‌های مشکل'), 'ReadingGoal': ('هدف مطالعه','اهداف مطالعه'), 'Review': ('نقد و امتیاز','نقدها و امتیازها'), 'SavedWord': ('واژه ذخیره‌شده','واژه‌های ذخیره‌شده'),
    'GamificationLevel': ('سطح بازی‌وارسازی','سطوح بازی‌وارسازی'), 'Badge': ('نشان','نشان‌ها'), 'UserBadge': ('نشان کاربر','نشان‌های کاربران'), 'XPEvent': ('رویداد تجربه','رویدادهای تجربه'), 'PointLedger': ('دفتر امتیاز','دفتر امتیازها'), 'Mission': ('ماموریت','ماموریت‌ها'), 'UserMission': ('ماموریت کاربر','ماموریت‌های کاربران'), 'UserStreak': ('روند پیوسته','روندهای پیوسته'), 'HallOfFameRecord': ('رکورد تالار افتخار','رکوردهای تالار افتخار'),
    'Event': ('رویداد تحلیلی','رویدادهای تحلیلی'), 'Notification': ('اعلان','اعلان‌ها'), 'PushSubscription': ('اشتراک پوش','اشتراک‌های پوش'), 'EmailLog': ('گزارش ایمیل','گزارش‌های ایمیل'), 'Ticket': ('تیکت','تیکت‌ها'), 'TicketMessage': ('پیام تیکت','پیام‌های تیکت'),
    'ArticleCategory': ('دسته مقاله','دسته‌های مقالات'), 'ArticleSource': ('منبع مقاله','منابع مقالات'), 'ArticleLibraryItem': ('آیتم کتابخانه مقاله','آیتم‌های کتابخانه مقاله'), 'ArticleAnnotation': ('یادداشت مقاله','یادداشت‌های مقاله'), 'Article': ('مقاله','مقالات'), 'ArticleTranslationVersion': ('نسخه ترجمه','نسخه‌های ترجمه'),
}
FIELD_LABELS = {
    'id':'شناسه','weekly_minutes':'دقایق هفتگی','weekly_books':'کتاب‌های هفتگی','completed_at':'زمان تکمیل','p256dh':'کلید پوش','auth':'کلید احراز پوش',
    'username':'نام کاربری','phone':'شماره تلفن','email':'ایمیل','first_name':'نام','last_name':'نام خانوادگی','avatar':'تصویر کاربر','wallet_balance':'موجودی کیف پول','xp':'تجربه','points':'امتیاز','purchase_points':'امتیاز خرید','study_points':'امتیاز مطالعه','leaderboard_public':'نمایش در رتبه‌بندی','referral_code':'کد دعوت','is_deactivated':'غیرفعال‌شده','terms_accepted_at':'زمان پذیرش قوانین',
    'user':'کاربر','name':'نام','token':'توکن','last_seen':'آخرین مشاهده','created_at':'زمان ایجاد','purpose':'کاربرد','expires_at':'زمان انقضا','attempts':'تعداد تلاش','used':'استفاده‌شده','session_key':'کلید نشست','device':'دستگاه','ip':'نشانی IP','user_agent':'مرورگر/دستگاه',
    'bio':'زندگی‌نامه','parent':'والد','slug':'نشانی','order':'ترتیب','min_xp':'حداقل تجربه','summary':'خلاصه','description':'توضیحات','author':'نویسنده','category':'دسته‌بندی','level':'سطح','price':'قیمت','old_price':'قیمت قبلی','cover':'تصویر جلد','pdf':'فایل PDF','audio':'فایل صوتی','visibility':'نوع دسترسی','subscription_included':'شامل اشتراک','featured':'پیشنهاد ویژه','access_password':'رمز دسترسی','status':'وضعیت','publish_at':'زمان انتشار','preview_percent':'درصد پیش‌نمایش','updated_at':'آخرین تغییر','book':'کتاب','title':'عنوان','text':'متن','duration':'مدت','file':'فایل','kind':'نوع',
    'code':'کد','percent':'درصد','amount':'مبلغ','capacity':'ظرفیت','min_order':'حداقل سفارش','active':'فعال','subtotal':'جمع اولیه','discount':'تخفیف','tax':'مالیات','total':'مبلغ نهایی','tracking_code':'کد پیگیری','gift_to':'هدیه به','source':'منبع','granted_at':'زمان اعطا','type':'نوع','reason':'دلیل','balance_before':'موجودی قبل','balance_after':'موجودی بعد','reference':'شناسه مرجع','checkout_request':'درخواست تسویه','provider':'ارائه‌دهنده','authority':'شناسه پرداخت','reference_id':'شماره مرجع','callback_payload':'داده بازگشت','idempotency_key':'کلید یکتایی درخواست','inviter':'دعوت‌کننده','invitee':'دعوت‌شونده','rewarded':'پاداش داده‌شده','duration_days':'مدت (روز)','grants_catalog_access':'دسترسی به کاتالوگ','plan':'طرح','starts_at':'شروع',
    'progress':'پیشرفت','current_page':'صفحه فعلی','current_chapter':'فصل فعلی','seconds':'ثانیه','audio_seconds':'زمان صوتی','position_seconds':'موقعیت صوت','duration_seconds':'مدت صوت','completed':'تکمیل‌شده','page':'صفحه','color':'رنگ','admin_score':'امتیاز مدیر','admin_reply':'پاسخ مدیر','approved':'تأییدشده','word':'واژه','normalized_word':'واژه نرمال‌شده','source_language':'زبان منبع','article':'مقاله','meaning_fa':'معنی فارسی','pronunciation_fa':'تلفظ فارسی','example_en':'مثال انگلیسی','last_reviewed':'آخرین مرور','review_count':'تعداد مرور',
    'icon':'آیکن','xp_reward':'پاداش تجربه','tier':'رده','badge':'نشان','earned_at':'زمان دریافت','point_type':'نوع امتیاز','revoked':'لغوشده','mission':'ماموریت','target':'هدف','study_points_reward':'پاداش مطالعه','period':'بازه','period_key':'کلید بازه','current_days':'روزهای فعلی','longest_days':'بیشترین روز','last_activity_date':'آخرین فعالیت','value':'مقدار','metadata':'فراداده',
    'is_active':'فعال','is_staff':'دسترسی مدیریت','is_superuser':'مدیر ارشد','groups':'گروه‌ها','user_permissions':'مجوزهای کاربر','date_joined':'تاریخ عضویت','last_login':'آخرین ورود','rating':'امتیاز','featured':'ویژه','is_valid':'معتبر','quality_score':'امتیاز کیفیت','translation_quality':'کیفیت ترجمه','translation_error':'خطای ترجمه','translation_version':'نسخه ترجمه','translation_hash':'هش ترجمه','translated_at':'زمان ترجمه','original_language':'زبان اصلی','authors':'نویسندگان','journal':'نشریه','doi':'DOI','citation_count':'تعداد استناد','relevance_score':'امتیاز ارتباط','last_discovered_at':'آخرین کشف','source_url':'نشانی منبع','pdf_url':'نشانی PDF','access':'نوع دسترسی','published':'منتشرشده','downloads':'تعداد مطالعه','cover':'تصویر','body':'متن','read_at':'زمان خواندن','endpoint':'نشانی سرویس','subject':'موضوع','priority':'اولویت','assigned_to':'مسئول','ticket':'تیکت',
    'base_url':'نشانی پایه','feed_url':'نشانی خوراک','source_type':'نوع منبع','is_active':'فعال','allow_full_republish':'اجازه بازنشر کامل','attribution_required':'ذکر منبع الزامی','notes':'یادداشت','favorite':'علاقه‌مندی','last_position':'آخرین موقعیت','reading_seconds':'زمان مطالعه','bookmarks':'نشانک‌ها','last_read_at':'آخرین مطالعه','selected_text':'متن انتخاب‌شده','note':'یادداشت','text_prefix':'متن قبل','text_suffix':'متن بعد','rects':'محدوده‌ها','title_fa':'عنوان فارسی','authors':'نویسندگان','original_language':'زبان اصلی','abstract':'چکیده اصلی','abstract_fa':'چکیده فارسی','full_text':'متن کامل اصلی','full_text_fa':'متن کامل فارسی','translation_status':'وضعیت ترجمه','translation_hash':'هش ترجمه','translation_version':'نسخه ترجمه','translation_quality':'کیفیت ترجمه','translation_error':'خطای ترجمه','translated_at':'زمان ترجمه','publication_date':'تاریخ انتشار','retrieved_at':'زمان دریافت','year':'سال','journal':'نشریه','doi':'DOI','source_provider':'ارائه‌دهنده منبع','external_id':'شناسه خارجی','citation_count':'تعداد استناد','relevance_score':'امتیاز ارتباط','last_discovered_at':'آخرین کشف','source_url':'نشانی منبع','pdf_url':'نشانی PDF','access':'دسترسی','published':'منتشرشده','downloads':'تعداد مطالعه','version':'نسخه','content_fa':'محتوای فارسی','quality_score':'امتیاز کیفیت','source_hash':'هش منبع','is_valid':'معتبر','error':'خطا','created_by':'ایجادکننده',
}
CHOICE_LABELS={'draft':'پیش‌نویس','scheduled':'زمان‌بندی‌شده','published':'منتشرشده','public':'عمومی','private':'خصوصی','password':'رمزدار','pending':'در انتظار','paid':'پرداخت‌شده','cancelled':'لغوشده','failed':'ناموفق','refunded':'بازپرداخت‌شده','active':'فعال','expired':'منقضی','credit':'واریز','debit':'برداشت','refund':'بازپرداخت','purchase':'خرید','subscription':'اشتراک','admin':'مدیر','info':'اطلاع','success':'موفق','warning':'هشدار','error':'خطا','open':'باز','external':'نسخه خارجی','translated':'ترجمه‌شده','translating':'در حال ترجمه','reviewed':'بازبینی‌شده','rss':'RSS','api':'API','manual':'دستی','in_progress':'در حال بررسی','waiting':'منتظر پاسخ','resolved':'حل‌شده','closed':'بسته','low':'کم','normal':'عادی','high':'زیاد','urgent':'فوری','daily':'روزانه','weekly':'هفتگی','monthly':'ماهانه','study':'مطالعه','unread':'خوانده‌نشده','reading':'در حال مطالعه','read':'خوانده‌شده','yellow':'زرد','green':'سبز','blue':'آبی','pink':'صورتی'}

def apply_admin_localization():
    # makemigrations compares runtime model metadata with migration state.  These
    # labels are admin presentation only, so never let them create schema-state
    # migrations.
    if 'makemigrations' in sys.argv:
        return
    for app_label, label in APP_LABELS.items():
        try: apps.get_app_config(app_label).verbose_name = label
        except LookupError: continue
    for model in apps.get_models():
        if model._meta.app_label not in APP_LABELS:
            continue
        labels=MODEL_LABELS.get(model.__name__)
        if labels:
            model._meta.verbose_name, model._meta.verbose_name_plural = labels
        for field in model._meta.fields:
            if field.name in FIELD_LABELS:
                field.verbose_name=FIELD_LABELS[field.name]
            if getattr(field,'choices',None):
                field.choices=[(value,CHOICE_LABELS.get(value,label)) for value,label in field.choices]

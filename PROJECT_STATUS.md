# وضعیت پروژه دانا

## تاریخ ممیزی

2026-09-16

## مسیر پروژه

`/home/ubuntu/dana`

## معماری فعلی

دانا یک پروژه Django مبتنی بر قالب‌های server-rendered است. تنظیمات در `core/settings.py` قرار دارد و از کاربر سفارشی `accounts.User` استفاده می‌کند. داده‌های توسعه در SQLite ذخیره می‌شوند و فایل‌های استاتیک با WhiteNoise سرو می‌شوند. URLهای اصلی در `core/urls.py` به appهای حساب کاربری، کتاب، فروش، مطالعه، گیمیفیکیشن، مقاله، اعلان، پشتیبانی، تحلیل و API متصل هستند.

## Appهای موجود

`accounts`, `books`, `shop`, `reader`, `gamification`, `analytics`, `notifications`, `support`, `api`, و `articles`.

## قابلیت‌های موجود

- احراز هویت پایه، پروفایل و کاربر سفارشی
- مدل کتاب، نویسنده، ناشر و دسته‌بندی و صفحات فهرست/جزئیات
- سبد خرید، checkout با کیف پول، سفارش، entitlement و تراکنش کیف پول
- مطالعه، پیشرفت مطالعه، bookmark، واژگان و review
- امتیاز خرید/مطالعه، streak و leaderboard
- referral، اعلان، مقاله و ابزارهای واردسازی/ترجمه
- تیکت پشتیبانی، داشبورد ابتدایی تحلیل، پنل Django admin و PWA manifest/service worker

## وضعیت فعلی و کمبودها

- پروژه در شاخه `main` و با یک commit اولیه دریافت شد؛ working tree در ابتدا clean بود.
- تست‌ها محدود به 5 تست در `shop` و `reader` هستند؛ `articles/tests.py` خالی است و برای accounts، books، API، gamification، notifications و support پوشش کافی وجود ندارد.
- داشبورد تحلیل فعلی فقط فروش، تعداد سفارش، کاربران و eventها را نشان می‌دهد و شاخص‌های کامل مأموریت مانند ARPU، LTV، نرخ تبدیل و active readers را ندارد.
- checkout داخل تراکنش atomic اجرا می‌شود، اما فهرست cart پیش از lock تراکنش خوانده می‌شود؛ برای بار هم‌زمان، idempotency کامل خرید باید با طراحی مجدد وضعیت cart/order و تست concurrency تکمیل شود.
- API ثبت event داده JSON نامعتبر را بدون پاسخ 400 مدیریت نمی‌کند و باید ورودی metadata را نیز محدود/اعتبارسنجی کند.
- ذخیره‌سازی و gateway واقعی پرداخت، ایمیل/OTP خارجی، صوت و ترجمه خارجی در این snapshot پیکربندی نشده‌اند.
- `staticfiles/` در محیط توسعه ساخته نشده است؛ این هشدار runtime است و خطای برنامه نیست.

## نتایج baseline

- `python3 manage.py check`: موفق، بدون issue
- `python3 manage.py makemigrations --check`: موفق، بدون migration معوق
- `python3 manage.py test`: موفق، 5 تست پاس‌شده
- هشدار غیرمسدودکننده: مسیر `staticfiles/` پیش از collectstatic وجود ندارد.

## بررسی امنیتی اولیه

CSRF middleware، auth decorators، `SECURE_CONTENT_TYPE_NOSNIFF`، کوکی secure در حالت non-debug و X-Frame-Options فعال هستند. با این حال، مقدار پیش‌فرض `SECRET_KEY` توسعه‌ای است و `AUTH_PASSWORD_VALIDATORS` خالی است؛ این دو مورد باید پیش از production با secret واقعی و validatorهای استاندارد تنظیم شوند. مسیرهای فایل upload و محدودیت حجم نیازمند hardening deployment هستند.

## وضعیت database

Migrationها موجود و همگام هستند. مدل‌های فروش برای `CartItem` و `Entitlement` محدودیت یکتا دارند و عملیات checkout از `transaction.atomic` و `select_for_update` برای کیف پول استفاده می‌کند. SQLite برای توسعه مناسب است اما برای production، PostgreSQL و تنظیمات backup/connection pooling لازم است.

## پیشنهاد مراحل بعدی

1. تکمیل اعتبارسنجی API و تست‌های accounts/books/shop.
2. ایمن‌سازی تنظیمات production و اجرای collectstatic.
3. بازطراحی checkout برای idempotency و تست race condition.
4. تکمیل analytics واقعی و پنل admin.
5. افزایش پوشش reader، gamification، referral، notifications، articles و support.
6. بررسی responsive/RTL با smoke test مرورگر و آماده‌سازی deployment PostgreSQL.

## تغییرات این مرحله

Baseline مستند شد و بررسی‌های Django و تست‌های موجود اجرا شدند. endpoint ثبت event اکنون JSON نامعتبر، payload غیرآبجکتی و metadata غیرآبجکتی را با پاسخ 400 رد می‌کند و برای آن سه تست regression اضافه شده است. checkout اکنون cart و entitlement را داخل transaction دوباره بررسی می‌کند و اعتبار coupon را پس از lock و پیش از مصرف مجدداً می‌سنجد؛ همچنین coupon در checkout ناموفق به‌دلیل موجودی ناکافی مصرف نمی‌شود.

پس از تغییرات، `python3 manage.py check`، `python3 manage.py makemigrations --check` و `python3 manage.py test` موفق بودند و مجموع تست‌ها از 5 به 8 رسید.

## ممیزی مرحله دوم

در ممیزی دوم، مسیرهای public و private با Django test client بررسی شدند. پیش از migration، اجرای واقعی Home روی دیتابیس توسعه به‌دلیل اعمال‌نشدن migrationها با خطای `no such table: articles_article` متوقف می‌شد؛ migrationهای موجود اعمال شدند و پس از آن smoke test همه مسیرهای اصلی با موفقیت انجام شد. صفحه Home، ورود، کتاب‌ها و مقالات برای مهمان و dashboard، profile، cart، wallet، vocabulary، notifications، support و leaderboard برای کاربر واردشده پاسخ صحیح دادند.

دو مشکل کدی نیز اصلاح شد: مسیر profile بدون `login_required` بود و مسیر ورود OTP در صورت داشتن referral به مدل `Referral` ارجاع می‌داد اما import آن وجود نداشت. برای هر دو مورد تست regression اضافه شد. بررسی مرورگر Home و Books نیز با HTTP موفق انجام شد و console مرورگر بدون خطا بود. برای اجرای sandbox، hostname موقت در متغیر محیطی `ALLOWED_HOSTS` قرار گرفت؛ این مقدار نباید به تنظیمات production hardcode شود.

در مرحله نهایی تست مشخص شد منطق ثبت `terms_accepted_at` و referral در OTP بیش از حد به شرط `created` وابسته بود؛ این منطق شفاف‌سازی شد و fixture تست نیز با session cookie واقعی همگام شد. نتیجه نهایی: 10 تست موفق.

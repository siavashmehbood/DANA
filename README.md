# دانا (DANA)

دانا یک پلتفرم فارسی و راست‌به‌چپ برای کشف، خرید و مطالعه کتاب‌های دیجیتال است. پروژه با Django و قالب‌های server-rendered ساخته شده و appهای حساب کاربری، کتاب، فروش، مطالعه، گیمیفیکیشن، مقاله، اعلان، پشتیبانی، تحلیل و API را در بر می‌گیرد.

## نیازمندی‌ها

- Python 3.11+
- Django 5.2+
- وابستگی‌های `requirements.txt`
- SQLite برای توسعه؛ PostgreSQL برای production

## نصب و اجرا

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver
```

## متغیرهای محیطی

مقادیر توسعه در `.env.example` مستند شده‌اند. هرگز `.env`، secret key، token، password یا credential را commit نکنید. در production مقدار `SECRET_KEY`، `DEBUG=0`، `ALLOWED_HOSTS`، تنظیمات database و سرویس ایمیل/پرداخت را با secret manager تنظیم کنید.

## Migration و داده

```bash
python manage.py makemigrations --check
python manage.py migrate
```

SQLite برای توسعه و تست است. برای استقرار واقعی، PostgreSQL، backup منظم media/database و محدودسازی دسترسی admin توصیه می‌شود.

## تست و بررسی کیفیت

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

## ساختار اصلی

| مسیر | مسئولیت |
|---|---|
| `core/` | تنظیمات، URL اصلی و صفحات عمومی |
| `accounts/` | کاربر سفارشی و احراز هویت |
| `books/` | مدل و صفحات کتاب |
| `shop/` | سبد خرید، سفارش، کیف پول و referral |
| `reader/` | پیشرفت مطالعه و ابزارهای خواندن |
| `gamification/` | امتیاز، streak و leaderboard |
| `templates/` | رابط فارسی و RTL |
| `static/` | CSS و JavaScript |

## استقرار

در production، `DEBUG` باید خاموش باشد، `SECRET_KEY` از محیط خوانده شود، `ALLOWED_HOSTS` محدود شود، HTTPS و secure cookies فعال باشند و فایل‌های media پشت storage مناسب قرار گیرند. اجرای `collectstatic` و بررسی migrationها پیش از release الزامی است.

وضعیت دقیق audit و کارهای باقی‌مانده در [PROJECT_STATUS.md](PROJECT_STATUS.md) ثبت شده است.


## Private media در production

فایل‌های محافظت‌شده کتاب (PDF، فایل صوتی کامل و صوت فصل‌ها) از storage جداگانه `PRIVATE_MEDIA_ROOT` خوانده می‌شوند و storage آن‌ها URL عمومی ندارد. این مسیر را **خارج از `MEDIA_ROOT` و هر alias عمومی وب‌سرور** قرار دهید. Nginx/Apache/CDN نباید `PRIVATE_MEDIA_ROOT` را مستقیماً publish کند؛ دسترسی فقط باید از endpointهای مجاز Django عبور کند تا entitlement/subscription expiry بررسی شود و Range request صوتی نیز حفظ شود.

نمونه production:

```env
MEDIA_ROOT=/srv/dana/public_media
PRIVATE_MEDIA_ROOT=/srv/dana/private_media
```

برای فایل‌های خصوصی موجود در استقرارهای قدیمی، قبل از release آن‌ها را از `MEDIA_ROOT/books/pdf`، `MEDIA_ROOT/books/audio` و `MEDIA_ROOT/chapters/audio` به ساختار متناظر زیر `PRIVATE_MEDIA_ROOT` منتقل کنید. این انتقال یک **EXTERNAL RELEASE REQUIREMENT** برای deployment دارای داده موجود است و نباید با public URL انجام شود.

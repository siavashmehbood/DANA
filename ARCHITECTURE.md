# معماری دانا

## نمای کلی

دانا یک monolith ماژولار Django است. هر قابلیت در app مستقل قرار دارد و از مدل‌های مشترک کاربر، کتاب و سفارش استفاده می‌کند. رابط کاربری با templateهای Django و CSS/JavaScript محلی ارائه می‌شود.

## جریان‌های اصلی

- **احراز هویت:** `accounts.User` به‌عنوان `AUTH_USER_MODEL` استفاده می‌شود و viewهای محافظت‌شده با `login_required` یا محدودیت staff اجرا می‌شوند.
- **کشف محتوا:** `books` و `articles` داده را با queryهای select-related به templateهای RTL می‌فرستند.
- **خرید:** کاربر کتاب را به `CartItem` اضافه می‌کند؛ checkout قیمت را از database می‌خواند، کیف پول را در transaction کم می‌کند، `Order`/`OrderItem`/`Entitlement` و `WalletTransaction` می‌سازد و امتیاز خرید می‌دهد.
- **مطالعه:** `reader` پیشرفت، bookmark و review را به کاربر و کتاب مرتبط می‌کند.
- **رویدادها:** endpoint احراز‌شده API رویدادهای تحلیلی را در `analytics.Event` ثبت می‌کند.

## مرزهای مسئولیت

Viewها orchestration درخواست و پاسخ را انجام می‌دهند؛ مدل‌ها محدودیت‌های رابطه‌ای و وضعیت را نگه می‌دارند؛ سرویس‌های `gamification` و `articles` منطق قابل استفاده مجدد را فراهم می‌کنند. عملیات مالی باید همیشه داخل `transaction.atomic` و با قفل ردیف کاربر انجام شود.

## پایگاه داده

SQLite برای توسعه پیکربندی شده است. migrationهای هر app در همان app نگهداری می‌شوند. محدودیت‌های مهم فعلی شامل یکتایی cart item، entitlement کاربر/کتاب و tracking code سفارش است.

## ملاحظات production

استفاده از PostgreSQL، secret manager، HTTPS، storage جداگانه برای media، backup، logging ساختاریافته و rate limiting برای endpointهای عمومی باید پیش از production تکمیل شود. جزئیات وضعیت و ریسک‌ها در [PROJECT_STATUS.md](PROJECT_STATUS.md) آمده است.

# Changelog

## Unreleased — 2026-09-16

- انجام audit اولیه repository و ثبت وضعیت واقعی در `PROJECT_STATUS.md`.
- افزودن راهنمای نصب، تست و استقرار در `README.md`.
- افزودن مستند معماری فعلی در `ARCHITECTURE.md`.
- baseline: Django check و migration check موفق؛ 5 تست موجود پاس شدند.
- بررسی و تکمیل اعتبارسنجی endpoint ثبت event و پوشش تست API.
- تکمیل اعتبارسنجی JSON و metadata در API ثبت event؛ payload نامعتبر اکنون پاسخ 400 می‌گیرد.
- تقویت مرز تراکنش checkout با بازخوانی cart/entitlement پس از lock و جلوگیری از مصرف coupon در پرداخت ناموفق.
- افزودن سه تست API؛ مجموع تست‌های پروژه به 8 تست رسید.
- رفع دسترسی ناخواسته مهمان به profile با افزودن `login_required`.
- رفع crash مسیر OTP هنگام ساخت referral با اصلاح import مدل `Referral`.
- افزودن تست‌های account برای profile خصوصی و referral در ورود OTP؛ مجموع تست‌ها به 10 رسید.
- افزودن focus state و پشتیبانی `prefers-reduced-motion` به CSS مشترک.
- اجرای smoke test واقعی مسیرهای اصلی پس از اعمال migrationهای دیتابیس توسعه و بررسی Home/Books در مرورگر.
- اصلاح منطق ثبت پذیرش قوانین در OTP و تکمیل fixture session برای تست referral؛ 10 تست نهایی موفق شدند.

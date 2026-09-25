from django.db import migrations


def seed_public_article(apps, schema_editor):
    Article = apps.get_model("articles", "Article")
    if Article.objects.filter(
        published=True
    ).filter(
        __import__("django").db.models.Q(full_text__gt="") |
        __import__("django").db.models.Q(full_text_fa__gt="") |
        __import__("django").db.models.Q(abstract__gt="") |
        __import__("django").db.models.Q(abstract_fa__gt="") |
        __import__("django").db.models.Q(pdf_url__gt="") |
        __import__("django").db.models.Q(pdf__gt="")
    ).exists():
        return
    Article.objects.get_or_create(
        slug="راهنمای-مطالعه-عمیق-دانا",
        defaults={
            "title": "A Practical Guide to Deep Reading",
            "title_fa": "راهنمای عملی مطالعه عمیق",
            "authors": "تحریریه دانا",
            "original_language": "fa",
            "abstract_fa": "مطالعه عمیق فقط بیشتر خواندن نیست؛ هدف، فهم بهتر، یادداشت‌برداری هدفمند و بازگشت آگاهانه به نکات مهم است.",
            "full_text_fa": (
                "برای مطالعه عمیق، پیش از شروع هدف خود را مشخص کنید. هنگام خواندن، نکات کلیدی را جدا کنید "
                "و پس از هر بخش، مفهوم اصلی را با زبان خودتان خلاصه کنید. وقفه‌های کوتاه و مرور دوره‌ای "
                "به تثبیت مطالب کمک می‌کند. در پایان، پرسش‌هایی که هنوز پاسخ نگرفته‌اند را ثبت کنید تا مسیر "
                "مطالعه بعدی روشن باشد."
            ),
            "translation_status": "reviewed",
            "featured": True,
            "published": True,
            "source_provider": "dana",
            "external_id": "dana-deep-reading-guide-v1",
        },
    )


def unseed_public_article(apps, schema_editor):
    Article = apps.get_model("articles", "Article")
    Article.objects.filter(external_id="dana-deep-reading-guide-v1", source_provider="dana").delete()


class Migration(migrations.Migration):
    dependencies = [("articles", "0012_translation_lifecycle_states")]
    operations = [migrations.RunPython(seed_public_article, unseed_public_article)]

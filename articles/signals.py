from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Article
from .services import schedule_article_processing


@receiver(post_save, sender=Article)
def process_article_after_save(sender, instance, created, update_fields=None, **kwargs):
    if not instance.published:
        return
    # Internal bookkeeping writes (translation status/version, analytics counters,
    # timestamps, etc.) must not enqueue another network-processing cycle.
    if update_fields is not None:
        source_fields={'title','abstract','full_text','pdf','pdf_url','published','source'}
        if not source_fields.intersection(update_fields):
            return
    transaction.on_commit(lambda: schedule_article_processing(instance.pk))

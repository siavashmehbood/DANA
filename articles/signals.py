from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Article
from .services import schedule_article_processing


@receiver(post_save, sender=Article)
def process_article_after_save(sender, instance, created, **kwargs):
    if not instance.published:
        return
    transaction.on_commit(lambda: schedule_article_processing(instance.pk))

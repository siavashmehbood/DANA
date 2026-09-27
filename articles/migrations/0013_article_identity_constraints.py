from django.db import migrations, models
from django.db.models import Count, Q


def _merge_duplicates(apps, schema_editor):
    Article = apps.get_model('articles', 'Article')
    Library = apps.get_model('articles', 'ArticleLibraryItem')
    Annotation = apps.get_model('articles', 'ArticleAnnotation')
    Version = apps.get_model('articles', 'ArticleTranslationVersion')

    groups = []
    for row in Article.objects.exclude(doi='').values('doi').annotate(n=Count('id')).filter(n__gt=1):
        groups.append(list(Article.objects.filter(doi=row['doi']).order_by('id').values_list('id', flat=True)))
    for row in Article.objects.exclude(source_provider='').exclude(external_id='').values('source_provider', 'external_id').annotate(n=Count('id')).filter(n__gt=1):
        groups.append(list(Article.objects.filter(source_provider=row['source_provider'], external_id=row['external_id']).order_by('id').values_list('id', flat=True)))

    seen = set()
    for ids in groups:
        ids = [pk for pk in ids if pk not in seen and Article.objects.filter(pk=pk).exists()]
        if len(ids) < 2:
            continue
        keep_id, duplicate_ids = ids[0], ids[1:]
        seen.update(duplicate_ids)

        # Library has a (user, article) uniqueness rule. Keep the user's existing
        # canonical row when both articles were saved; otherwise repoint it.
        for duplicate_id in duplicate_ids:
            for item in Library.objects.filter(article_id=duplicate_id):
                if Library.objects.filter(user_id=item.user_id, article_id=keep_id).exists():
                    item.delete()
                else:
                    item.article_id = keep_id
                    item.save(update_fields=['article'])
            Annotation.objects.filter(article_id=duplicate_id).update(article_id=keep_id)

            # Translation versions also have per-article version uniqueness.
            used_versions = set(Version.objects.filter(article_id=keep_id).values_list('version', flat=True))
            next_version = max(used_versions or {0}) + 1
            for version in Version.objects.filter(article_id=duplicate_id).order_by('version', 'id'):
                if version.version in used_versions:
                    version.version = next_version
                    next_version += 1
                used_versions.add(version.version)
                version.article_id = keep_id
                version.save(update_fields=['article', 'version'])

            Article.objects.filter(pk=duplicate_id).delete()


class Migration(migrations.Migration):
    dependencies = [('articles', '0012_translation_lifecycle_states')]
    operations = [
        migrations.RunPython(_merge_duplicates, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='article',
            constraint=models.UniqueConstraint(
                fields=('doi',),
                condition=~Q(doi=''),
                name='unique_article_nonempty_doi',
            ),
        ),
        migrations.AddConstraint(
            model_name='article',
            constraint=models.UniqueConstraint(
                fields=('source_provider', 'external_id'),
                condition=~Q(source_provider='') & ~Q(external_id=''),
                name='unique_article_provider_external_id',
            ),
        ),
    ]

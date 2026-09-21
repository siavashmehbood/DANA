from django.test import TestCase
from django.urls import reverse
from .models import Article, ArticleCategory, ArticleLibraryItem, ArticleAnnotation, ArticleTranslationVersion
from accounts.models import User

class ArticleFlowTests(TestCase):
    def setUp(self):
        self.category=ArticleCategory.objects.create(name='Science',slug='science')
        self.article=Article.objects.create(title='Test Article',slug='test-article',category=self.category,published=True,full_text='Test article content')

    def test_published_article_is_visible(self):
        response=self.client.get(reverse('article_detail',args=[self.article.slug]))
        self.assertEqual(response.status_code,200)

    def test_unpublished_article_is_not_public(self):
        self.article.published=False; self.article.save(update_fields=['published'])
        response=self.client.get(reverse('article_detail',args=[self.article.slug]))
        self.assertEqual(response.status_code,404)

    def test_citation_export_is_available(self):
        response=self.client.get(reverse('article_citation_export',args=[self.article.slug])+'?format=bibtex')
        self.assertEqual(response.status_code,200)
        self.assertIn(b'@article', response.content)

    def test_authenticated_research_library_and_progress(self):
        user=User.objects.create_user(username='researcher',password='secret')
        self.client.force_login(user)
        response=self.client.get(reverse('article_library'))
        self.assertEqual(response.status_code,200)
        response=self.client.post(reverse('article_reading_progress',args=[self.article.slug]), {'progress':42,'position':180,'seconds':30})
        self.assertEqual(response.status_code,200)
        item=ArticleLibraryItem.objects.get(user=user,article=self.article)
        self.assertEqual(item.progress,42)
        self.assertEqual(item.status,'reading')

    def test_annotation_create_and_delete_are_owner_scoped(self):
        user=User.objects.create_user(username='annotator',password='secret')
        self.client.force_login(user)
        response=self.client.post(reverse('article_annotation_create',args=[self.article.slug]), {'selected_text':'important finding','kind':'highlight'})
        self.assertEqual(response.status_code,200)
        annotation=ArticleAnnotation.objects.get(user=user,article=self.article)
        response=self.client.post(reverse('article_annotation_delete',args=[annotation.pk]))
        self.assertEqual(response.status_code,200)
        self.assertFalse(ArticleAnnotation.objects.filter(pk=annotation.pk).exists())

    def test_pdf_reader_requires_pdf_and_redirects_cleanly(self):
        user=User.objects.create_user(username='pdfuser',password='secret')
        self.client.force_login(user)
        response=self.client.get(reverse('article_pdf_reader',args=[self.article.slug]))
        self.assertEqual(response.status_code,302)
        self.assertEqual(response.url,reverse('article_detail',args=[self.article.slug]))

    def test_pdf_annotation_persists_rects_and_color(self):
        user=User.objects.create_user(username='pdfannotator',password='secret')
        self.client.force_login(user)
        response=self.client.post(reverse('article_annotation_create',args=[self.article.slug]), {'selected_text':'PDF evidence','kind':'highlight','color':'blue','page':3,'rects':'[{"page":3,"x":0.1,"y":0.2,"w":0.3,"h":0.04}]'})
        self.assertEqual(response.status_code,200)
        item=ArticleAnnotation.objects.get(user=user,article=self.article)
        self.assertEqual(item.color,'blue')
        self.assertEqual(item.rects[0]['page'],3)
    def test_annotation_update_is_owner_scoped(self):
        user=User.objects.create_user(username='noteowner',password='secret')
        self.client.force_login(user)
        self.client.post(reverse('article_annotation_create',args=[self.article.slug]), {'selected_text':'quote','kind':'note'})
        annotation=ArticleAnnotation.objects.get(user=user,article=self.article)
        response=self.client.post(reverse('article_annotation_update',args=[annotation.pk]), {'note':'Research note','color':'green'})
        self.assertEqual(response.status_code,200)
        annotation.refresh_from_db()
        self.assertEqual(annotation.note,'Research note')
        self.assertEqual(annotation.color,'green')

    def test_bookmark_toggle_persists(self):
        user=User.objects.create_user(username='bookmarkuser',password='secret')
        self.client.force_login(user)
        response=self.client.post(reverse('article_bookmark_toggle',args=[self.article.slug]), {'page':7})
        self.assertEqual(response.status_code,200)
        item=ArticleLibraryItem.objects.get(user=user,article=self.article)
        self.assertEqual(item.bookmarks,[7])
        response=self.client.post(reverse('article_bookmark_toggle',args=[self.article.slug]), {'page':7})
        self.assertEqual(response.status_code,200)
        item.refresh_from_db()
        self.assertEqual(item.bookmarks,[])

    def test_annotation_rects_are_sanitized(self):
        user=User.objects.create_user(username='rectuser',password='secret')
        self.client.force_login(user)
        payload='[{"page":3,"x":-2,"y":2,"w":0.4,"h":0.02},{"page":"bad"},{"x":0,"y":0,"w":0,"h":0}]'
        response=self.client.post(reverse('article_annotation_create',args=[self.article.slug]), {'selected_text':'safe','rects':payload})
        self.assertEqual(response.status_code,200)
        annotation=ArticleAnnotation.objects.get(user=user,article=self.article)
        self.assertEqual(len(annotation.rects),1)
        self.assertEqual(annotation.rects[0]['x'],0)
        self.assertEqual(annotation.rects[0]['y'],1)


class TranslationHistoryTests(TestCase):
    def setUp(self):
        self.article = Article.objects.create(
            title='Original title', slug='translation-history',
            abstract='Original abstract', full_text='Original body', published=True,
        )

    def test_translation_creates_version_without_overwriting_original(self):
        from unittest.mock import patch
        from .translation import translate_article
        original = (self.article.title, self.article.abstract, self.article.full_text)
        with patch('articles.translation.translate_text', side_effect=['عنوان فارسی', 'چکیده فارسی', 'متن فارسی']):
            translate_article(self.article, full_text=True, force=True)
        self.article.refresh_from_db()
        self.assertEqual((self.article.title, self.article.abstract, self.article.full_text), original)
        self.assertEqual(self.article.full_text_fa, 'متن فارسی')
        self.assertEqual(self.article.translation_version, 1)
        self.assertEqual(ArticleTranslationVersion.objects.filter(article=self.article).count(), 1)

    def test_failed_translation_keeps_previous_valid_persian_content(self):
        from unittest.mock import patch
        from .translation import translate_article
        self.article.title_fa = 'ترجمه سالم'
        self.article.full_text_fa = 'متن سالم'
        self.article.translation_version = 1
        self.article.save()
        with patch('articles.translation.translate_text', side_effect=RuntimeError('provider unavailable')):
            translate_article(self.article, full_text=True, force=True)
        self.article.refresh_from_db()
        self.assertEqual(self.article.title_fa, 'ترجمه سالم')
        self.assertEqual(self.article.full_text_fa, 'متن سالم')
        self.assertEqual(self.article.translation_status, 'failed')
        self.assertIn('provider unavailable', self.article.translation_error)


class ArticleAdminTranslationTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser(username='article-admin', password='secret', email='admin@example.com')
        self.client.force_login(self.staff)
        self.article = Article.objects.create(title='Admin translation', slug='admin-translation', full_text='Body', published=True)

    def test_admin_can_rollback_to_previous_valid_translation(self):
        ArticleTranslationVersion.objects.create(article=self.article, version=1, title_fa='نسخه یک', content_fa='متن یک', source_hash='one')
        ArticleTranslationVersion.objects.create(article=self.article, version=2, title_fa='نسخه دو', content_fa='متن دو', source_hash='two')
        self.article.title_fa = 'نسخه دو'
        self.article.full_text_fa = 'متن دو'
        self.article.translation_version = 2
        self.article.translation_hash = 'two'
        self.article.save()
        response = self.client.post(
            reverse('admin:articles_article_changelist'),
            {'action': 'rollback_translation', '_selected_action': [self.article.pk]},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.article.refresh_from_db()
        self.assertEqual(self.article.translation_version, 1)
        self.assertEqual(self.article.full_text_fa, 'متن یک')
        self.assertEqual(self.article.translation_status, 'reviewed')

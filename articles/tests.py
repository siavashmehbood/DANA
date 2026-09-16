from django.test import TestCase
from django.urls import reverse
from .models import Article, ArticleCategory, ArticleLibraryItem, ArticleAnnotation
from accounts.models import User

class ArticleFlowTests(TestCase):
    def setUp(self):
        self.category=ArticleCategory.objects.create(name='Science',slug='science')
        self.article=Article.objects.create(title='Test Article',slug='test-article',category=self.category,published=True)

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

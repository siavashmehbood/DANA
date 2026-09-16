from django.test import TestCase
from django.urls import reverse
from .models import Article, ArticleCategory

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

from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from accounts.models import User
from books.models import Author, Book
from shop.models import Entitlement
from reader.models import Review

class ProtectedMediaTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='reader',password='pass12345')
        author=Author.objects.create(name='Author')
        self.book=Book.objects.create(name='Private Book',slug='private-book',author=author,status='published',visibility='private',pdf=SimpleUploadedFile('book.pdf',b'%PDF-1.4 test',content_type='application/pdf'))
        self.url=reverse('protected_book_pdf',args=[self.book.pk])

    def test_pdf_requires_authentication(self):
        response=self.client.get(self.url)
        self.assertEqual(response.status_code,302)

    def test_pdf_requires_entitlement(self):
        self.client.login(username='reader',password='pass12345')
        self.assertEqual(self.client.get(self.url).status_code,403)

    def test_expired_entitlement_cannot_open_pdf(self):
        Entitlement.objects.create(user=self.user,book=self.book,expires_at=timezone.now()-timedelta(seconds=1))
        self.client.login(username='reader',password='pass12345')
        self.assertEqual(self.client.get(self.url).status_code,403)

    def test_pdf_is_available_to_entitled_user(self):
        Entitlement.objects.create(user=self.user,book=self.book)
        self.client.login(username='reader',password='pass12345')
        response=self.client.get(self.url)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response['Content-Type'],'application/pdf')


class ScheduledPublicationTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(name='Schedule Author')
        self.future = Book.objects.create(name='Future Book', slug='future-book', author=self.author, status='scheduled', publish_at=timezone.now()+timedelta(days=1))
        self.live = Book.objects.create(name='Live Book', slug='live-book', author=self.author, status='scheduled', publish_at=timezone.now()-timedelta(minutes=1))

    def test_future_scheduled_book_is_not_public(self):
        self.assertNotContains(self.client.get(reverse('books')), 'Future Book')
        self.assertEqual(self.client.get(reverse('book_detail', args=[self.future.slug])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('home')), 'Future Book')

    def test_due_scheduled_book_is_public(self):
        self.assertContains(self.client.get(reverse('books')), 'Live Book')
        self.assertEqual(self.client.get(reverse('book_detail', args=[self.live.slug])).status_code, 200)


class SeoEndpointTests(TestCase):
    def test_robots_blocks_private_surfaces_and_links_sitemap(self):
        response=self.client.get('/robots.txt')
        self.assertContains(response,'Disallow: /protected/')
        self.assertContains(response,'sitemap.xml')

    def test_sitemap_only_contains_published_books(self):
        author=Author.objects.create(name='SEO Author')
        Book.objects.create(name='Visible SEO',slug='visible-seo',author=author,status='published')
        Book.objects.create(name='Draft SEO',slug='draft-seo',author=author,status='draft')
        response=self.client.get('/sitemap.xml')
        self.assertContains(response,'visible-seo')
        self.assertNotContains(response,'draft-seo')


    def test_canonical_url_drops_query_string(self):
        response=self.client.get('/books/?q=test')
        self.assertContains(response,'rel="canonical" href="http://testserver/books/"')


class HomeDiscoveryTests(TestCase):
    def test_popular_shelf_uses_only_approved_reviews(self):
        author=Author.objects.create(name='Home Author')
        approved=Book.objects.create(name='Approved popular',slug='approved-popular',author=author,status='published')
        hidden=Book.objects.create(name='Hidden popular',slug='hidden-popular',author=author,status='published')
        user1=User.objects.create_user(username='home-r1',password='pass12345')
        user2=User.objects.create_user(username='home-r2',password='pass12345')
        Review.objects.create(user=user1,book=approved,rating=3,text='ok',approved=True)
        Review.objects.create(user=user2,book=hidden,rating=5,text='hidden',approved=False)
        response=self.client.get(reverse('home'))
        popular=list(response.context['popular'])
        self.assertLess(popular.index(approved),popular.index(hidden))


class RecommendationTests(TestCase):
    def test_high_rating_category_drives_recommendation(self):
        from books.models import Category
        category=Category.objects.create(name='Recommended',slug='recommended')
        author=Author.objects.create(name='Recommend Author')
        rated=Book.objects.create(name='Rated',slug='rated-book',author=author,category=category,status='published')
        candidate=Book.objects.create(name='Candidate',slug='candidate-book',author=author,category=category,status='published')
        user=User.objects.create_user(username='recommender',password='pass12345')
        Review.objects.create(user=user,book=rated,rating=5,text='great',approved=True)
        self.client.force_login(user)
        response=self.client.get(reverse('home'))
        self.assertIn(candidate,list(response.context['recommendations']))

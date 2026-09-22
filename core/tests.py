from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from accounts.models import User
from books.models import Author, Book
from shop.models import Entitlement, SubscriptionPlan, Subscription
from reader.models import Review, ReadingProgress

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


    def test_new_user_gets_cold_start_recommendations(self):
        author=Author.objects.create(name='Cold Author')
        book=Book.objects.create(name='Cold Candidate',slug='cold-candidate',author=author,status='published')
        user=User.objects.create_user(username='cold-user',password='pass12345')
        self.client.force_login(user)
        response=self.client.get(reverse('home'))
        self.assertIn(book,list(response.context['recommendations']))


    def test_home_categories_hide_empty_and_future_only_categories(self):
        from books.models import Category
        active=Category.objects.create(name='Active category',slug='active-category')
        future_only=Category.objects.create(name='Future category',slug='future-category')
        author=Author.objects.create(name='Category Author')
        Book.objects.create(name='Live category book',slug='live-category-book',author=author,category=active,status='published')
        Book.objects.create(name='Future category book',slug='future-category-book',author=author,category=future_only,status='scheduled',publish_at=timezone.now()+timedelta(days=1))
        response=self.client.get(reverse('home'))
        categories=list(response.context['categories'])
        self.assertIn(active,categories)
        self.assertNotIn(future_only,categories)


    def test_subscription_catalog_plan_allows_legacy_protected_pdf(self):
        user=User.objects.create_user(username='legacy-reader',password='pass12345')
        author=Author.objects.create(name='Legacy PDF Author')
        book=Book.objects.create(name='Legacy PDF Book',slug='legacy-pdf-book',author=author,status='published',visibility='private',subscription_included=True)
        plan=SubscriptionPlan.objects.create(name='Legacy PDF',slug='legacy-pdf',price=0,duration_days=7,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=2))
        self.client.force_login(user)
        response=self.client.get(reverse('protected_book_pdf',args=[book.pk]))
        self.assertNotEqual(response.status_code,403)


    def test_service_worker_does_not_cache_private_reader_routes(self):
        response=self.client.get(reverse('service_worker'))
        body=response.content.decode()
        self.assertIn("url.pathname.startsWith('/static/')||CORE.includes(url.pathname)",body)
        self.assertNotIn("c.put(event.request,copy));}return response;}).catch(()=>caches.match(event.request).then",body)
        self.assertNotIn("caches.match('/')",body)


    def test_home_continue_reading_includes_free_public_book(self):
        user=User.objects.create_user(username='free-home-reader',password='pass12345')
        author=Author.objects.create(name='Free Home Author')
        book=Book.objects.create(name='Free Home Book',slug='free-home-book',author=author,status='published',visibility='public',price=0)
        ReadingProgress.objects.create(user=user,book=book,progress=25,current_page=4)
        self.client.force_login(user)
        response=self.client.get(reverse('home'))
        self.assertIn(book,[item.book for item in response.context['continue_reading']])

    def test_home_continue_reading_includes_subscription_book(self):
        user=User.objects.create_user(username='sub-home-reader',password='pass12345')
        author=Author.objects.create(name='Sub Home Author')
        book=Book.objects.create(name='Sub Home Book',slug='sub-home-book',author=author,status='published',visibility='private',subscription_included=True)
        plan=SubscriptionPlan.objects.create(name='Home Catalog',slug='home-catalog',price=0,duration_days=7,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=2))
        ReadingProgress.objects.create(user=user,book=book,progress=30,current_page=5)
        self.client.force_login(user)
        response=self.client.get(reverse('home'))
        self.assertIn(book,[item.book for item in response.context['continue_reading']])


    def test_expired_entitlement_does_not_hide_recommendation(self):
        from books.models import Category
        category=Category.objects.create(name='Expired rec',slug='expired-rec')
        author=Author.objects.create(name='Expired Rec Author')
        expired=Book.objects.create(name='Expired Owned',slug='expired-owned',author=author,category=category,status='published')
        candidate=Book.objects.create(name='Expired Candidate',slug='expired-candidate',author=author,category=category,status='published')
        user=User.objects.create_user(username='expired-rec-user',password='pass12345')
        Entitlement.objects.create(user=user,book=expired,source='purchase',expires_at=timezone.now()-timedelta(days=1))
        Review.objects.create(user=user,book=expired,rating=5,text='liked',approved=True)
        self.client.force_login(user)
        response=self.client.get(reverse('home'))
        self.assertIn(candidate,list(response.context['recommendations']))
        self.assertIn(expired,list(response.context['recommendations']))


    def test_protected_pdf_sets_private_security_headers(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        user=User.objects.create_user(username='pdf-header-user',password='pass12345')
        author=Author.objects.create(name='PDF Header Author')
        book=Book.objects.create(name='PDF Header',slug='pdf-header',author=author,status='published',visibility='private',pdf=SimpleUploadedFile('sample.pdf',b'%PDF-1.4 test',content_type='application/pdf'))
        Entitlement.objects.create(user=user,book=book,source='admin')
        self.client.force_login(user)
        response=self.client.get(reverse('protected_book_pdf',args=[book.pk]))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response['Cache-Control'],'private, no-store')
        self.assertEqual(response['X-Content-Type-Options'],'nosniff')
        self.assertIn("frame-ancestors 'self'",response['Content-Security-Policy'])
        self.assertEqual(response['X-Robots-Tag'],'noindex, nofollow')
        self.assertEqual(response['Referrer-Policy'],'same-origin')


    def test_subscription_accessible_book_is_not_recommended(self):
        from books.models import Category
        category=Category.objects.create(name='Sub rec',slug='sub-rec')
        author=Author.objects.create(name='Sub Rec Author')
        accessible=Book.objects.create(name='Already accessible',slug='already-accessible',author=author,category=category,status='published',subscription_included=True)
        candidate=Book.objects.create(name='Buy candidate',slug='buy-candidate',author=author,category=category,status='published')
        user=User.objects.create_user(username='sub-rec-user',password='pass12345')
        plan=SubscriptionPlan.objects.create(name='Rec Catalog',slug='rec-catalog',price=0,duration_days=7,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=2))
        Review.objects.create(user=user,book=accessible,rating=5,text='liked',approved=True)
        self.client.force_login(user)
        response=self.client.get(reverse('home'))
        recs=list(response.context['recommendations'])
        self.assertNotIn(accessible,recs)
        self.assertIn(candidate,recs)


    def test_protected_pdf_rejects_non_pdf_extension(self):
        user=User.objects.create_user(username='bad-pdf-user',password='pass12345')
        author=Author.objects.create(name='Bad PDF Author')
        book=Book.objects.create(name='Bad PDF',slug='bad-pdf',author=author,status='published',visibility='private',pdf=SimpleUploadedFile('payload.html',b'<script>alert(1)</script>',content_type='text/html'))
        Entitlement.objects.create(user=user,book=book,source='admin')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('protected_book_pdf',args=[book.pk])).status_code,404)


    def test_service_worker_has_update_cache_headers(self):
        response=self.client.get(reverse('service_worker'))
        self.assertEqual(response['Cache-Control'],'no-cache')
        self.assertEqual(response['Service-Worker-Allowed'],'/')


class HomePrivacyTests(TestCase):
    def test_authenticated_home_is_not_cacheable(self):
        user=User.objects.create_user(username='private-home',password='pass12345')
        self.client.force_login(user)
        response=self.client.get('/')
        self.assertIn('private',response['Cache-Control'])
        self.assertIn('no-store',response['Cache-Control'])
        self.assertIn('Cookie',response['Vary'])


    def test_service_worker_does_not_precache_personalized_home(self):
        response=self.client.get('/sw.js')
        body=response.content.decode()
        self.assertIn("CORE=[]",body)
        self.assertNotIn("CORE=['/",body)


class BaseMetadataTests(TestCase):
    def test_catalog_uses_single_canonical_url_and_page_description(self):
        response=self.client.get('/books/?q=test')
        html=response.content.decode()
        self.assertEqual(html.count('rel="canonical"'),1)
        self.assertIn('جستجو و کشف کتاب',html)

    def test_library_is_noindex(self):
        user=User.objects.create_user(username='private-library',password='pass12345')
        self.client.force_login(user)
        response=self.client.get('/library/')
        self.assertContains(response,'name="robots" content="noindex,nofollow"')


    def test_public_discovery_metadata_has_safe_cache_headers(self):
        for path in ('/robots.txt','/sitemap.xml'):
            response=self.client.get(path)
            self.assertIn('public',response['Cache-Control'])
            self.assertEqual(response['X-Content-Type-Options'],'nosniff')


    def test_sitemap_excludes_unreadable_articles(self):
        from articles.models import Article
        Article.objects.create(title='Empty Article',slug='empty-article',published=True)
        Article.objects.create(title='Readable Article',slug='readable-article',published=True,abstract='Readable')
        response=self.client.get('/sitemap.xml')
        self.assertNotContains(response,'empty-article')
        self.assertContains(response,'readable-article')


    def test_sitemap_excludes_password_protected_books(self):
        author=Author.objects.create(name='Protected SEO')
        Book.objects.create(name='Protected',slug='protected-seo',author=author,status='published',visibility='password',access_password='secret')
        response=self.client.get('/sitemap.xml')
        self.assertNotContains(response,'protected-seo')


    def test_sitemap_contains_valid_book_path(self):
        author=Author.objects.create(name='Sitemap Author')
        Book.objects.create(name='Sitemap Book',slug='sitemap-book',author=author,status='published',visibility='public')
        response=self.client.get('/sitemap.xml')
        self.assertContains(response,'/books/sitemap-book/')


    def test_anonymous_home_renders_successfully(self):
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)


    def test_home_discovery_excludes_password_protected_books(self):
        author=Author.objects.create(name='Home Protected')
        Book.objects.create(name='Hidden Home Book',slug='hidden-home-book',author=author,status='published',visibility='password',access_password='secret')
        response=self.client.get('/')
        self.assertNotContains(response,'Hidden Home Book')


    def test_subscription_cannot_open_private_pdf(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from shop.models import SubscriptionPlan, Subscription
        author=Author.objects.create(name='Private PDF Author')
        book=Book.objects.create(name='Private PDF',slug='private-pdf-sub',author=author,status='published',visibility='private',subscription_included=True,price=100,pdf=SimpleUploadedFile('private.pdf',b'%PDF-1.4 test',content_type='application/pdf'))
        user=User.objects.create_user(username='private-pdf-user',password='pass12345')
        plan=SubscriptionPlan.objects.create(name='Catalog PDF',slug='catalog-pdf',price=10,duration_days=30,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=2))
        self.client.login(username='private-pdf-user',password='pass12345')
        response=self.client.get(reverse('protected_book_pdf',args=[book.pk]))
        self.assertEqual(response.status_code,403)


    def test_home_does_not_offer_private_subscription_book_as_readable(self):
        user=User.objects.create_user(username='private-home-sub',password='pass12345')
        author=Author.objects.create(name='Private Home Author')
        book=Book.objects.create(name='Hidden Subscription',slug='hidden-sub-home',author=author,status='published',visibility='private',subscription_included=True,price=100)
        ReadingProgress.objects.create(user=user,book=book,progress=25)
        plan=SubscriptionPlan.objects.create(name='Home Catalog',slug='home-catalog',price=10,duration_days=30,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=2))
        self.client.login(username='private-home-sub',password='pass12345')
        response=self.client.get(reverse('home'))
        self.assertNotContains(response,'Hidden Subscription')

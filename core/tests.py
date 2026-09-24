from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from accounts.models import User
from books.models import Author, Book
from shop.models import Entitlement, Subscription, SubscriptionPlan
from reader.models import Review, ReadingProgress, AudioProgress

class HealthEndpointTests(TestCase):
    def test_liveness_and_readiness_are_available(self):
        health=self.client.get(reverse('healthz'))
        ready=self.client.get(reverse('readyz'))
        self.assertEqual(health.status_code,200)
        self.assertEqual(ready.status_code,200)
        self.assertEqual(health.json()['status'],'ok')
        self.assertEqual(ready.json()['status'],'ready')
        self.assertEqual(health['Cache-Control'],'no-store')
        self.assertEqual(ready['Cache-Control'],'no-store')


class PrivateMediaConfigurationTests(TestCase):
    def test_private_media_root_rejects_public_media_root_or_children(self):
        from core.settings import validate_private_media_root
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            public=Path(root)/'media'
            with self.assertRaises(RuntimeError):
                validate_private_media_root(public, public)
            with self.assertRaises(RuntimeError):
                validate_private_media_root(public, public/'private')


class PrivateStorageIsolationTests(TestCase):
    def test_protected_book_files_have_no_public_media_url(self):
        from books.models import Book, Chapter
        for field_name in ('pdf','audio'):
            storage=Book._meta.get_field(field_name).storage
            self.assertIsNone(storage.base_url)
            self.assertNotEqual(storage.location, str(settings.MEDIA_ROOT))
        chapter_storage=Chapter._meta.get_field('audio').storage
        self.assertIsNone(chapter_storage.base_url)
        self.assertNotEqual(chapter_storage.location, str(__import__('django').conf.settings.MEDIA_ROOT))


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


    def test_subscription_accessible_unengaged_book_can_be_recommended(self):
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
        self.assertIn(accessible,recs)
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




class RetiredPlanPdfAccessTests(TestCase):
    def test_retired_subscription_plan_keeps_protected_pdf_entitlement(self):
        user=User.objects.create_user(username='retired-pdf',password='pass12345')
        author=Author.objects.create(name='PDF Author')
        from django.core.files.uploadedfile import SimpleUploadedFile
        book=Book.objects.create(name='Protected Subscription PDF',slug='protected-sub-pdf',author=author,status='published',price=100,subscription_included=True,pdf=SimpleUploadedFile('book.pdf',b'%PDF-1.4 test',content_type='application/pdf'))
        plan=SubscriptionPlan.objects.create(name='Old Plan',slug='old-plan',price=10,duration_days=30,active=False,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,starts_at=timezone.now()-timezone.timedelta(days=1),expires_at=timezone.now()+timezone.timedelta(days=2),status='active')
        self.client.force_login(user)
        response=self.client.get(reverse('protected_book_pdf',args=[book.pk]))
        self.assertEqual(response.status_code,200)


    def test_unpublished_pdf_returns_404_even_with_entitlement(self):
        user=User.objects.create_user(username='draft-pdf-user',password='pass12345')
        author=Author.objects.create(name='Draft PDF Author')
        from django.core.files.uploadedfile import SimpleUploadedFile
        book=Book.objects.create(name='Draft PDF',slug='draft-protected-pdf',author=author,status='draft',price=100,pdf=SimpleUploadedFile('draft.pdf',b'%PDF-1.4 test',content_type='application/pdf'))
        Entitlement.objects.create(user=user,book=book,source='admin')
        self.client.force_login(user)
        response=self.client.get(reverse('protected_book_pdf',args=[book.pk]))
        self.assertEqual(response.status_code,404)


    def test_password_book_pdf_cannot_bypass_reader_gate(self):
        user=User.objects.create_user(username='password-pdf-user',password='pass12345')
        author=Author.objects.create(name='Password Author')
        from django.core.files.uploadedfile import SimpleUploadedFile
        book=Book.objects.create(name='Password PDF',slug='password-pdf',author=author,status='published',price=0,visibility='password',access_password='secret',pdf=SimpleUploadedFile('password.pdf',b'%PDF-1.4 test',content_type='application/pdf'))
        self.client.force_login(user)
        response=self.client.get(reverse('protected_book_pdf',args=[book.pk]))
        self.assertEqual(response.status_code,403)


class AudioHomeIntegrationTests(TestCase):
    def test_home_surfaces_continue_listening(self):
        user=User.objects.create_user(username='audio-home',password='pass12345')
        author=Author.objects.create(name='Audio Home Author')
        book=Book.objects.create(name='Audio Home Book',slug='audio-home-book',author=author,status='published',visibility='public',price=0,audio=SimpleUploadedFile('home.mp3',b'ID3home',content_type='audio/mpeg'))
        AudioProgress.objects.create(user=user,book=book,position_seconds=42,duration_seconds=200)
        self.client.force_login(user)
        response=self.client.get(reverse('home'))
        self.assertIn(book,[item.book for item in response.context['continue_listening']])

    def test_active_reading_category_influences_recommendations(self):
        from books.models import Category
        category=Category.objects.create(name='Reading interest',slug='reading-interest')
        author=Author.objects.create(name='Reading Interest Author')
        current=Book.objects.create(name='Current interest',slug='current-interest',author=author,category=category,status='published')
        candidate=Book.objects.create(name='Next interest',slug='next-interest',author=author,category=category,status='published')
        user=User.objects.create_user(username='interest-user',password='pass12345')
        ReadingProgress.objects.create(user=user,book=current,progress=30)
        self.client.force_login(user)
        response=self.client.get(reverse('home'))
        self.assertIn(candidate,list(response.context['recommendations']))


class AudioRangeTests(TestCase):
    def test_entitled_audio_supports_byte_ranges(self):
        user=User.objects.create_user(username='range-user',password='pass12345')
        author=Author.objects.create(name='Range Author')
        payload=b'ID3'+b'a'*100
        book=Book.objects.create(name='Range Audio',slug='range-audio',author=author,status='published',visibility='private',audio=SimpleUploadedFile('range.mp3',payload,content_type='audio/mpeg'))
        Entitlement.objects.create(user=user,book=book,source='purchase')
        self.client.force_login(user)
        response=self.client.get(reverse('book_secure_file',args=[book.pk,'audio']),HTTP_RANGE='bytes=3-12')
        self.assertEqual(response.status_code,206)
        self.assertEqual(response['Content-Range'],f'bytes 3-12/{len(payload)}')
        self.assertEqual(response.content,b'a'*10)


class HomeSubscriberRecommendationTests(TestCase):
    def test_active_subscriber_home_recommends_unengaged_catalog_title(self):
        from datetime import timedelta
        from django.utils import timezone
        from accounts.models import User
        from books.models import Author, Book, Category
        from shop.models import Entitlement, Subscription, SubscriptionPlan
        user=User.objects.create_user(username='home-subscriber-recs',password='pass12345')
        author=Author.objects.create(name='Home Subscriber Author')
        category=Category.objects.create(name='Home Subscriber Category',slug='home-subscriber-category')
        seed=Book.objects.create(name='Home Seed',slug='home-seed',author=author,category=category,status='published',visibility='public')
        candidate=Book.objects.create(name='Home Catalog Candidate',slug='home-catalog-candidate',author=author,category=category,status='published',visibility='public',subscription_included=True)
        Entitlement.objects.create(user=user,book=seed)
        plan=SubscriptionPlan.objects.create(name='Home Catalog',slug='home-catalog-plan',price=100,duration_days=30,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=29))
        self.client.force_login(user)
        response=self.client.get(reverse('home'))
        self.assertIn(candidate,list(response.context['recommendations']))


class HomeLatestActivityTests(TestCase):
    def test_home_hero_resumes_newer_audio_activity(self):
        user=User.objects.create_user(username='home-latest-activity',password='pass12345')
        author=Author.objects.create(name='Home Latest Author')
        text_book=Book.objects.create(name='Older Reading',slug='older-reading',author=author,status='published',visibility='public',price=0)
        audio_book=Book.objects.create(name='Newer Listening',slug='newer-listening',author=author,status='published',visibility='public',price=0,audio=SimpleUploadedFile('latest.mp3',b'ID3latest',content_type='audio/mpeg'))
        ReadingProgress.objects.create(user=user,book=text_book,progress=25,current_page=2)
        AudioProgress.objects.create(user=user,book=audio_book,position_seconds=90,duration_seconds=500)
        self.client.force_login(user)
        response=self.client.get(reverse('home'))
        self.assertEqual(response.context['continue_item']['book'],audio_book)
        self.assertEqual(response.context['continue_item']['kind'],'audio')
        self.assertContains(response,reverse('audio_player',args=[audio_book.id]))


class HomeAudioOnlyLegacyResumeTests(TestCase):
    def test_audio_only_book_with_legacy_reading_progress_routes_to_audio_player(self):
        user=User.objects.create_user(username='home-audio-legacy',password='pass12345')
        author=Author.objects.create(name='Home Audio Legacy Author')
        book=Book.objects.create(name='Home Audio Legacy',slug='home-audio-legacy',author=author,status='published',visibility='public',price=0,audio=SimpleUploadedFile('legacy.mp3',b'ID3legacy',content_type='audio/mpeg'))
        ReadingProgress.objects.create(user=user,book=book,progress=20,current_page=1)
        self.client.force_login(user)
        response=self.client.get(reverse('home'))
        self.assertEqual(response.context['continue_item']['kind'],'audio')
        self.assertContains(response,reverse('audio_player',args=[book.id]))


class AudioRecommendationSignalTests(TestCase):
    def test_listening_category_influences_home_recommendations(self):
        from books.models import Category
        category=Category.objects.create(name='Audio Interest',slug='audio-interest')
        author=Author.objects.create(name='Audio Interest Author')
        current=Book.objects.create(name='Current Audio Interest',slug='current-audio-interest',author=author,category=category,status='published',visibility='public',price=0,audio=SimpleUploadedFile('current.mp3',b'ID3',content_type='audio/mpeg'))
        candidate=Book.objects.create(name='Next Audio Interest',slug='next-audio-interest',author=author,category=category,status='published',visibility='public',price=0,audio=SimpleUploadedFile('next.mp3',b'ID3',content_type='audio/mpeg'))
        user=User.objects.create_user(username='audio-interest-user',password='pass12345')
        AudioProgress.objects.create(user=user,book=current,position_seconds=60,duration_seconds=300)
        self.client.force_login(user)
        response=self.client.get(reverse('home'))
        self.assertIn(candidate,list(response.context['recommendations']))
        self.assertNotIn(current,list(response.context['recommendations']))




class AdminPersianLocalizationTests(TestCase):
    def test_management_apps_models_and_fields_have_persian_labels(self):
        from django.apps import apps
        from core.admin_localization import apply_admin_localization
        apply_admin_localization()
        expected_apps={'accounts':'کاربران و حساب‌ها','books':'کتاب‌ها و محتوا','shop':'فروش و اشتراک','reader':'مطالعه و یادداشت‌ها','gamification':'بازی‌وارسازی','analytics':'تحلیل و رویدادها','notifications':'اعلان‌ها','support':'پشتیبانی','articles':'مقالات'}
        for app_label,label in expected_apps.items():
            self.assertEqual(apps.get_app_config(app_label).verbose_name,label)
        checks=[('accounts','User','phone','شماره تلفن'),('books','Book','price','قیمت'),('shop','Payment','authority','شناسه پرداخت'),('reader','ReadingProgress','progress','پیشرفت'),('gamification','XPEvent','reason','دلیل'),('analytics','Event','metadata','فراداده'),('notifications','Notification','read_at','زمان خواندن'),('support','Ticket','assigned_to','مسئول'),('articles','Article','translation_status','وضعیت ترجمه')]
        for app_label,model_name,field_name,label in checks:
            model=apps.get_model(app_label,model_name)
            self.assertTrue(any('\u0600' <= ch <= '\u06ff' for ch in str(model._meta.verbose_name)))
            self.assertEqual(model._meta.get_field(field_name).verbose_name,label)

    def test_admin_translation_choice_labels_are_persian(self):
        from django.apps import apps
        from core.admin_localization import apply_admin_localization
        apply_admin_localization()
        choices=dict(apps.get_model('articles','Article')._meta.get_field('translation_status').choices)
        self.assertEqual(choices['pending'],'در انتظار')
        self.assertEqual(choices['failed'],'ناموفق')


class PublicDiscoveryCacheTests(TestCase):
    def test_anonymous_discovery_pages_are_short_lived_public_cacheable(self):
        author=Author.objects.create(name='Cache Author')
        book=Book.objects.create(name='Cache Book',slug='cache-book',author=author,status='published',visibility='public')
        from articles.models import Article
        article=Article.objects.create(title='Cache Article',slug='cache-article',abstract='Readable abstract',published=True)
        for path in (reverse('home'),reverse('books'),reverse('book_detail',args=[book.slug]),reverse('article_list'),reverse('article_detail',args=[article.slug])):
            response=self.client.get(path)
            self.assertEqual(response.status_code,200)
            self.assertIn('public',response['Cache-Control'])

    def test_authenticated_catalog_is_not_shared_cacheable(self):
        user=User.objects.create_user(username='cache-auth',password='pass12345')
        self.client.force_login(user)
        for path in (reverse('home'),reverse('books'),reverse('article_list')):
            response=self.client.get(path)
            self.assertIn('private',response['Cache-Control'])
            self.assertIn('no-store',response['Cache-Control'])


class PersianAdminDashboardTests(TestCase):
    def test_custom_dashboard_is_active_and_persian(self):
        user=User.objects.create_superuser(username='dashboard-admin',password='pass12345',email='dash@example.com')
        self.client.force_login(user)
        response=self.client.get('/admin/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'داشبورد مدیریت دانا')
        self.assertContains(response,'کتاب‌ها')
        self.assertContains(response,'فروشگاه')

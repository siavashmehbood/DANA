from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User
from shop.models import Entitlement, SubscriptionPlan, Subscription
from .models import Author, Book, Chapter, Category
from reader.models import Review
from analytics.models import Event

class ProtectedMediaTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='media-user',password='pass12345')
        author=Author.objects.create(name='Author')
        self.book=Book.objects.create(name='Private audio',slug='private-audio',author=author,status='published',visibility='private')
        self.chapter=Chapter.objects.create(book=self.book,title='Chapter 1',order=1,audio=SimpleUploadedFile('c1.mp3',b'audio'))
    def test_chapter_audio_requires_entitlement(self):
        self.client.force_login(self.user)
        url=reverse('chapter_secure_audio',args=[self.book.pk,self.chapter.pk])
        self.assertEqual(self.client.get(url).status_code,403)
        Entitlement.objects.create(user=self.user,book=self.book,source='admin')
        self.assertEqual(self.client.get(url).status_code,200)
    def test_chapter_from_another_book_cannot_be_injected(self):
        other=Book.objects.create(name='Other',slug='other',author=self.book.author,status='published',visibility='public')
        self.client.force_login(self.user)
        url=reverse('chapter_secure_audio',args=[other.pk,self.chapter.pk])
        self.assertEqual(self.client.get(url).status_code,404)


class DiscoveryTests(TestCase):
    def setUp(self):
        self.author=Author.objects.create(name='Discovery Author')
        self.text=Book.objects.create(name='Text',slug='text-discovery',author=self.author,status='published',price=0,pdf=SimpleUploadedFile('text.pdf',b'pdf'))
        self.audio=Book.objects.create(name='Audio',slug='audio-discovery',author=self.author,status='published',price=100,audio=SimpleUploadedFile('audio.mp3',b'audio'))
    def test_format_filter(self):
        response=self.client.get(reverse('books'),{'kind':'audio'})
        self.assertContains(response,'Audio')
        self.assertNotContains(response,'Text')
    def test_price_filter(self):
        response=self.client.get(reverse('books'),{'price':'free'})
        self.assertContains(response,'Text')
        self.assertNotContains(response,'Audio')


    def test_persian_search_matches_arabic_character_variant(self):
        Book.objects.create(name='کتاب یک',slug='persian-search',author=self.author,status='published')
        response=self.client.get(reverse('books'),{'q':'كتاب يك'})
        self.assertContains(response,'کتاب یک')


class CatalogPaginationTests(TestCase):
    def test_catalog_paginates_without_losing_results(self):
        author=Author.objects.create(name='Catalog Author')
        for i in range(26):
            Book.objects.create(name=f'Book {i}',slug=f'book-{i}',author=author,status='published')
        response=self.client.get(reverse('books'))
        self.assertEqual(len(response.context['books']),24)
        self.assertEqual(response.context['total_count'],26)
        second=self.client.get(reverse('books')+'?page=2')
        self.assertEqual(len(second.context['books']),2)


class PersianSearchTests(TestCase):
    def test_search_normalizes_arabic_persian_letters_and_half_space(self):
        author=Author.objects.create(name='کیان')
        Book.objects.create(name='کتاب خوب',slug='persian-search',author=author,status='published')
        response=self.client.get(reverse('books'),{'q':'كتاب\u200cخوب'})
        self.assertContains(response,'کتاب خوب')


    def test_search_relaxes_multiword_zero_result_query(self):
        author=Author.objects.create(name='Search Author')
        Book.objects.create(name='کتاب نمونه',slug='relaxed-search',author=author,status='published')
        response=self.client.get(reverse('books'),{'q':'کتاب ناموجود'})
        self.assertContains(response,'کتاب نمونه')


    def test_zero_result_search_is_tracked(self):
        self.client.get(reverse('books'),{'q':'واژهکاملاًناموجود'})
        self.assertTrue(Event.objects.filter(name='search_zero_result').exists())


    def test_search_event_records_result_count(self):
        author=Author.objects.create(name='Count Author')
        Book.objects.create(name='نتیجه شمار',slug='count-result',author=author,status='published')
        self.client.get(reverse('books'),{'q':'نتیجه'})
        event=Event.objects.filter(name='search').latest('created_at')
        self.assertEqual(event.value,1)


    def test_relaxed_search_keeps_price_filter(self):
        author=Author.objects.create(name='Filter Author')
        Book.objects.create(name='کتاب رایگان',slug='free-relaxed',author=author,status='published',price=0)
        Book.objects.create(name='کتاب پولی',slug='paid-relaxed',author=author,status='published',price=100)
        response=self.client.get(reverse('books'),{'q':'کتاب ناموجود','price':'free'})
        self.assertContains(response,'کتاب رایگان')
        self.assertNotContains(response,'کتاب پولی')


    def test_relaxed_search_marks_response_for_user(self):
        author=Author.objects.create(name='UX Author')
        Book.objects.create(name='نمونه جستجو',slug='relaxed-ux',author=author,status='published')
        response=self.client.get(reverse('books'),{'q':'نمونه ناشناخته'})
        self.assertTrue(response.context['used_relaxed_search'])
        self.assertContains(response,'نزدیک‌ترین نتایج مرتبط')


class CatalogRankingTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='ranker',password='pass12345')
        self.author=Author.objects.create(name='Rank Author')

    def test_rating_sort_ignores_unapproved_reviews(self):
        low=Book.objects.create(name='Low approved',slug='low-approved',author=self.author,status='published')
        hidden=Book.objects.create(name='Hidden high',slug='hidden-high',author=self.author,status='published')
        Review.objects.create(user=self.user,book=low,rating=2,text='ok',approved=True)
        other=User.objects.create_user(username='ranker2',password='pass12345')
        Review.objects.create(user=other,book=hidden,rating=5,text='hidden',approved=False)
        response=self.client.get(reverse('books'),{'sort':'rating'})
        names=[b.name for b in response.context['books']]
        self.assertLess(names.index('Low approved'),names.index('Hidden high'))


    def test_invalid_catalog_filters_fall_back_safely(self):
        response=self.client.get(reverse('books'),{'sort':'bad','kind':'bad','price':'bad'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['sort'],'new')
        self.assertEqual(response.context['kind'],'all')
        self.assertEqual(response.context['price'],'all')


    def test_paginating_search_does_not_duplicate_search_event(self):
        self.client.get(reverse('books'),{'q':'نمونه'})
        before=Event.objects.filter(name='search').count()
        self.client.get(reverse('books'),{'q':'نمونه','page':'2'})
        self.assertEqual(Event.objects.filter(name='search').count(),before)


    def test_relaxed_search_preserves_requested_sort(self):
        author=Author.objects.create(name='Sort Author')
        Book.objects.create(name='نمونه گران',slug='relaxed-expensive',author=author,status='published',price=200)
        Book.objects.create(name='نمونه ارزان',slug='relaxed-cheap',author=author,status='published',price=10)
        response=self.client.get(reverse('books'),{'q':'نمونه ناموجود','sort':'price_low'})
        names=[b.name for b in response.context['books']]
        self.assertEqual(names[:2],['نمونه ارزان','نمونه گران'])


    def test_search_reports_when_query_was_normalized(self):
        response=self.client.get(reverse('books'),{'q':'كتاب'})
        self.assertTrue(response.context['query_was_normalized'])


    def test_invalid_page_value_falls_back_to_first_page(self):
        response=self.client.get(reverse('books'),{'page':'invalid'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['page_obj'].number,1)


    def test_nonpositive_page_value_falls_back_to_first_page(self):
        response=self.client.get(reverse('books'),{'page':'0'})
        self.assertEqual(response.context['page_obj'].number,1)


    def test_alef_maqsura_query_is_normalized(self):
        response=self.client.get(reverse('books'),{'q':'على'})
        self.assertEqual(response.context['q'],'علی')
        self.assertTrue(response.context['query_was_normalized'])


    def test_search_event_records_filter_context(self):
        self.client.get(reverse('books'),{'q':'نمونه','kind':'audio','price':'paid','sort':'rating'})
        event=Event.objects.filter(name='search',metadata__kind='audio').latest('created_at')
        self.assertEqual(event.metadata['kind'],'audio')
        self.assertEqual(event.metadata['price'],'paid')
        self.assertEqual(event.metadata['sort'],'rating')


    def test_unknown_category_filter_is_ignored(self):
        response=self.client.get(reverse('books'),{'cat':'missing-category'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['cat'],'')


class SubscriptionBookAccessTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='subscriber',password='pass12345')
        author=Author.objects.create(name='Subscription Author')
        self.book=Book.objects.create(name='Subscriber Book',slug='subscriber-book',author=author,status='published',visibility='private',subscription_included=True,pdf=SimpleUploadedFile('sub.pdf',b'%PDF-1.4 test',content_type='application/pdf'))
        self.client.login(username='subscriber',password='pass12345')

    def test_active_catalog_subscription_grants_private_book_access(self):
        plan=SubscriptionPlan.objects.create(name='Catalog',slug='catalog-access',price=100,duration_days=30,grants_catalog_access=True)
        Subscription.objects.create(user=self.user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=5))
        response=self.client.get(reverse('book_detail',args=[self.book.slug]))
        self.assertTrue(response.context['has_access'])
        media=self.client.get(reverse('book_secure_file',args=[self.book.pk,'pdf']))
        self.assertEqual(media.status_code,200)

    def test_subscription_without_catalog_access_does_not_grant_private_book(self):
        plan=SubscriptionPlan.objects.create(name='Basic',slug='basic-no-catalog',price=10,duration_days=30,grants_catalog_access=False)
        Subscription.objects.create(user=self.user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=5))
        response=self.client.get(reverse('book_detail',args=[self.book.slug]))
        self.assertFalse(response.context['has_access'])


    def test_private_book_detail_offers_subscription_when_locked(self):
        response=self.client.get(reverse('book_detail',args=[self.book.slug]))
        self.assertFalse(response.context['has_access'])
        self.assertContains(response,reverse('subscriptions'))


    def test_protected_media_disables_shared_caching(self):
        import tempfile
        from django.core.files.base import ContentFile
        user=User.objects.create_user(username='media-cache-user',password='pass12345')
        author=Author.objects.create(name='Media Cache Author')
        book=Book.objects.create(name='Private media',slug='private-media-cache',author=author,status='published',visibility='private')
        book.audio.save('private.mp3',ContentFile(b'audio-bytes'),save=True)
        from shop.models import Entitlement
        Entitlement.objects.create(user=user,book=book,source='purchase')
        self.client.login(username='media-cache-user',password='pass12345')
        response=self.client.get(reverse('book_secure_file',args=[book.pk,'audio']))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response['Cache-Control'],'private, no-store')
        self.assertIn('Cookie',response['Vary'])
        self.assertEqual(response['X-Content-Type-Options'],'nosniff')


    def test_paid_public_book_detail_requires_purchase(self):
        user=User.objects.create_user(username='paid-public-user',password='pass12345')
        author=Author.objects.create(name='Paid Public Author')
        book=Book.objects.create(name='Paid Public',slug='paid-public',author=author,status='published',visibility='public',price=5000)
        self.client.force_login(user)
        response=self.client.get(reverse('book_detail',args=[book.slug]))
        self.assertFalse(response.context['has_access'])
        self.assertContains(response,'افزودن به سبد')


    def test_private_book_is_hidden_from_public_catalog_and_detail(self):
        author=Author.objects.create(name='Hidden Author')
        private=Book.objects.create(name='Hidden Book',slug='hidden-book',author=author,status='published',visibility='private')
        listing=self.client.get(reverse('books'))
        self.assertNotContains(listing,'Hidden Book')
        detail=self.client.get(reverse('book_detail',args=[private.slug]))
        self.assertEqual(detail.status_code,404)


    def test_relaxed_search_never_leaks_private_books(self):
        author=Author.objects.create(name='Private Search Author')
        Book.objects.create(name='راز پنهان',slug='private-relaxed',author=author,status='published',visibility='private')
        response=self.client.get(reverse('books'),{'q':'راز ناشناخته'})
        self.assertNotContains(response,'راز پنهان')


    def test_subscription_catalog_filter_only_shows_included_books(self):
        author=Author.objects.create(name='Subscription Filter Author')
        included=Book.objects.create(name='Included Filter',slug='included-filter',author=author,status='published',subscription_included=True)
        Book.objects.create(name='Excluded Filter',slug='excluded-filter',author=author,status='published',subscription_included=False)
        response=self.client.get(reverse('books'),{'access':'subscription'})
        self.assertContains(response,included.name)
        self.assertNotContains(response,'Excluded Filter')


class BookMediaValidationTests(TestCase):
    def test_book_pdf_rejects_non_pdf_extension(self):
        from django.core.exceptions import ValidationError
        from django.core.files.uploadedfile import SimpleUploadedFile
        author=Author.objects.create(name='Media Author')
        book=Book(name='Unsafe Media',slug='unsafe-media',author=author,status='draft',pdf=SimpleUploadedFile('payload.exe',b'MZ'))
        with self.assertRaises(ValidationError):
            book.full_clean()


class BookDetailPrivacyTests(TestCase):
    def test_authenticated_book_detail_is_not_cacheable(self):
        user=User.objects.create_user(username='detail-private',password='pass12345')
        author=Author.objects.create(name='Detail Author')
        book=Book.objects.create(name='Detail Book',slug='detail-private-book',author=author,status='published')
        self.client.force_login(user)
        response=self.client.get(reverse('book_detail',args=[book.slug]))
        self.assertIn('private',response['Cache-Control'])
        self.assertIn('Cookie',response['Vary'])


class BookSlugTests(TestCase):
    def test_blank_and_duplicate_slugs_are_generated_safely(self):
        author=Author.objects.create(name='Slug Author')
        first=Book.objects.create(name='کتاب تکراری',slug='',author=author,status='published')
        second=Book.objects.create(name='کتاب تکراری',slug='',author=author,status='published')
        self.assertTrue(first.slug)
        self.assertNotEqual(first.slug,second.slug)


    def test_generated_unicode_slug_detail_route_resolves(self):
        author=Author.objects.create(name='Route Author')
        book=Book.objects.create(name='کتاب فارسی مسیر',slug='',author=author,status='published')
        response=self.client.get(reverse('book_detail',args=[book.slug]))
        self.assertEqual(response.status_code,200)


class BookValidationTests(TestCase):
    def setUp(self):
        self.author=Author.objects.create(name='Validation Author')

    def test_password_book_requires_password(self):
        from django.core.exceptions import ValidationError
        book=Book(name='Locked',slug='locked-validation',author=self.author,visibility='password')
        with self.assertRaises(ValidationError):
            book.full_clean()

    def test_scheduled_book_requires_publish_time(self):
        from django.core.exceptions import ValidationError
        book=Book(name='Scheduled',slug='scheduled-validation',author=self.author,status='scheduled')
        with self.assertRaises(ValidationError):
            book.full_clean()

    def test_old_price_cannot_be_below_current_price(self):
        from django.core.exceptions import ValidationError
        book=Book(name='Price',slug='price-validation',author=self.author,price=100,old_price=50)
        with self.assertRaises(ValidationError):
            book.full_clean()


    def test_non_password_book_rejects_access_password(self):
        from django.core.exceptions import ValidationError
        book=Book(name='Public password',slug='public-password-validation',author=self.author,visibility='public',access_password='secret')
        with self.assertRaises(ValidationError):
            book.full_clean()


    def test_non_scheduled_book_rejects_publish_time(self):
        from django.core.exceptions import ValidationError
        book=Book(name='Immediate',slug='immediate-validation',author=self.author,status='published',publish_at=timezone.now()+timedelta(days=1))
        with self.assertRaises(ValidationError):
            book.full_clean()


    def test_scheduled_book_requires_future_time(self):
        from django.core.exceptions import ValidationError
        book=Book(name='Past scheduled',slug='past-scheduled-validation',author=self.author,status='scheduled',publish_at=timezone.now()-timedelta(minutes=1))
        with self.assertRaises(ValidationError):
            book.full_clean()


    def test_public_catalog_hides_private_and_password_books(self):
        author=Author.objects.create(name='Visibility Author')
        Book.objects.create(name='Public Catalog Book',slug='public-catalog-book',author=author,status='published',visibility='public')
        Book.objects.create(name='Private Catalog Book',slug='private-catalog-book',author=author,status='published',visibility='private')
        Book.objects.create(name='Password Catalog Book',slug='password-catalog-book',author=author,status='published',visibility='password',access_password='secret')
        response=self.client.get(reverse('books'))
        self.assertContains(response,'Public Catalog Book')
        self.assertNotContains(response,'Private Catalog Book')
        self.assertNotContains(response,'Password Catalog Book')


    def test_password_book_detail_is_hidden_without_unlock(self):
        author=Author.objects.create(name='Hidden Password Author')
        Book.objects.create(name='Hidden Password Detail',slug='hidden-password-detail',author=author,status='published',visibility='password',access_password='secret')
        response=self.client.get(reverse('book_detail',args=['hidden-password-detail']))
        self.assertEqual(response.status_code,404)


    def test_related_recommendations_exclude_password_books(self):
        author=Author.objects.create(name='Related Author')
        category=Category.objects.create(name='Related Category',slug='related-category')
        main=Book.objects.create(name='Main Public',slug='main-public',author=author,category=category,status='published',visibility='public')
        Book.objects.create(name='Locked Related',slug='locked-related',author=author,category=category,status='published',visibility='password',access_password='secret')
        response=self.client.get(reverse('book_detail',args=[main.slug]))
        self.assertNotContains(response,'Locked Related')


    def test_unknown_protected_media_kind_is_not_disclosed(self):
        user=User.objects.create_user(username='unknown-media-user',password='pass12345')
        author=Author.objects.create(name='Unknown Media Author')
        book=Book.objects.create(name='Unknown Media Book',slug='unknown-media-book',author=author,status='published',visibility='private')
        self.client.force_login(user)
        response=self.client.get(reverse('book_secure_file',args=[book.pk,'unknown']))
        self.assertEqual(response.status_code,404)


    def test_subscription_private_detail_is_noindex_and_private_cache(self):
        user=User.objects.create_user(username='private-seo-user',password='pass12345')
        author=Author.objects.create(name='Private SEO Author')
        book=Book.objects.create(name='Private SEO Book',slug='private-seo-book',author=author,status='published',visibility='private',subscription_included=True)
        plan=SubscriptionPlan.objects.create(name='Catalog SEO',slug='catalog-seo',price=0,duration_days=30,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=5))
        self.client.force_login(user)
        response=self.client.get(reverse('book_detail',args=[book.slug]))
        self.assertEqual(response.headers.get('X-Robots-Tag'),'noindex, nofollow')
        self.assertIn('no-store',response.headers.get('Cache-Control',''))

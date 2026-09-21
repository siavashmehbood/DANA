from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User
from shop.models import Entitlement
from .models import Author, Book, Chapter
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
        self.assertEqual(self.client.get(url).status_code,403)


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

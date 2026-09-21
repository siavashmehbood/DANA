from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from accounts.models import User
from books.models import Author, Book
from shop.models import Entitlement

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
        self.assertNotContains(self.client.get(reverse('book_list')), 'Future Book')
        self.assertEqual(self.client.get(reverse('book_detail', args=[self.future.slug])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('home')), 'Future Book')

    def test_due_scheduled_book_is_public(self):
        self.assertContains(self.client.get(reverse('book_list')), 'Live Book')
        self.assertEqual(self.client.get(reverse('book_detail', args=[self.live.slug])).status_code, 200)

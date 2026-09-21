from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User
from shop.models import Entitlement
from .models import Author, Book, Chapter

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

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Author, Book


class BookDiscoveryTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(name='نویسنده آزمایشی')
        self.published = Book.objects.create(
            name='کتاب ی فارسی',
            slug='persian-book',
            author=self.author,
            price=10000,
            status='published',
            visibility='public',
        )
        Book.objects.create(
            name='کتاب آینده',
            slug='future-book',
            author=self.author,
            price=20000,
            status='scheduled',
            publish_at=timezone.now() + timedelta(days=2),
            visibility='public',
        )

    def test_scheduled_books_are_not_public(self):
        response = self.client.get(reverse('books'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'کتاب ی فارسی')
        self.assertNotContains(response, 'کتاب آینده')

    def test_arabic_persian_keyboard_variants_search(self):
        response = self.client.get(reverse('books'), {'q': 'کتاب ي'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'کتاب ی فارسی')

    def test_invalid_sort_is_safe_and_deterministic(self):
        response = self.client.get(reverse('books'), {'sort': 'not-a-sort'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'کتاب ی فارسی')

    def test_book_detail_hides_unpublished_book(self):
        scheduled = Book.objects.create(
            name='کتاب زمان‌بندی',
            slug='scheduled-detail',
            author=self.author,
            status='scheduled',
            publish_at=timezone.now() + timedelta(days=1),
            visibility='public',
        )
        response = self.client.get(reverse('book_detail', args=[scheduled.slug]))
        self.assertEqual(response.status_code, 404)

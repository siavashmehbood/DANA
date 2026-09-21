from django.test import TestCase
from accounts.models import User
from books.models import Author, Book, Chapter
from gamification.models import PointLedger, UserStreak
from .models import ReadingProgress, Review
from django.urls import reverse


class StudyFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reader', password='pass123')
        author = Author.objects.create(name='Study Author')
        self.book = Book.objects.create(
            name='Study Book', slug='study-book', author=author,
            price=0, status='published', visibility='public'
        )
        self.client.login(username='reader', password='pass123')

    def test_progress_updates_streak(self):
        response = self.client.post(
            reverse('reader_progress', args=[self.book.pk]),
            {'progress': '20', 'page': '4', 'seconds': '120'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ReadingProgress.objects.filter(user=self.user, book=self.book).exists())
        self.assertTrue(UserStreak.objects.filter(user=self.user, current_days=1).exists())

    def test_admin_score_is_saved_for_leaderboard(self):
        review = Review.objects.create(
            user=self.user, book=self.book, rating=5, admin_score=8, approved=True
        )
        self.assertEqual(review.admin_score, 8)


    def test_progress_rejects_chapter_from_another_book(self):
        other = Book.objects.create(name='Other Book', slug='other-book', author=self.book.author, status='published', visibility='public')
        foreign_chapter = Chapter.objects.create(book=other, title='Foreign', order=1)
        response = self.client.post(
            reverse('reader_progress', args=[self.book.pk]),
            {'progress': '20', 'page': '4', 'chapter_id': foreign_chapter.pk},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ReadingProgress.objects.filter(user=self.user, book=self.book).exists())


    def test_reader_denies_unpublished_book(self):
        draft = Book.objects.create(name='Draft Book', slug='draft-book', author=self.book.author, status='draft', visibility='public')
        self.assertEqual(self.client.get(reverse('reader', args=[draft.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('reader_progress', args=[draft.pk]), {'progress':'1'}).status_code, 403)


    def test_notes_deny_unpublished_book(self):
        draft = Book.objects.create(name='Draft Notes', slug='draft-notes', author=self.book.author, status='draft', visibility='public')
        self.assertEqual(self.client.post(reverse('reader_note', args=[draft.pk]), {'page':'1','text':'x'}).status_code, 403)

    def test_bookmark_page_is_bounded(self):
        response=self.client.post(reverse('reader_bookmark',args=[self.book.pk]),{'page':'999999999','title':'far'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['page'],1000000)

from django.test import TestCase
from accounts.models import User
from books.models import Author, Book
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

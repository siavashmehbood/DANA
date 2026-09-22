from django.test import TestCase
from accounts.models import User
from books.models import Author, Book, Chapter
from gamification.models import PointLedger, UserStreak
from shop.models import Entitlement
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


    def test_review_requires_access_and_is_moderated(self):
        private=Book.objects.create(name='Review private',slug='review-private',author=self.book.author,status='published',visibility='private')
        url=reverse('reader_review',args=[private.pk])
        self.assertEqual(self.client.post(url,{'rating':'5','text':'Great'}).status_code,403)
        Entitlement.objects.create(user=self.user,book=private,source='admin')
        response=self.client.post(url,{'rating':'5','text':'Great'})
        self.assertEqual(response.status_code,200)
        review=Review.objects.get(user=self.user,book=private)
        self.assertEqual(review.rating,5)
        self.assertFalse(review.approved)

    def test_review_rejects_invalid_rating(self):
        response=self.client.post(reverse('reader_review',args=[self.book.pk]),{'rating':'9','text':'Bad rating'})
        self.assertEqual(response.status_code,400)


    def test_editing_review_resets_moderation(self):
        Review.objects.create(user=self.user,book=self.book,rating=5,text='old',approved=True,admin_score=8,admin_reply='ok')
        response=self.client.post(reverse('reader_review',args=[self.book.pk]),{'rating':'4','text':'edited'})
        self.assertEqual(response.status_code,200)
        review=Review.objects.get(user=self.user,book=self.book)
        self.assertFalse(review.approved)
        self.assertIsNone(review.admin_score)
        self.assertEqual(review.admin_reply,'')


    def test_bookmark_same_page_is_idempotent_and_updates_title(self):
        url=reverse('reader_bookmark',args=[self.book.pk])
        first=self.client.post(url,{'page':'7','title':'اول'})
        second=self.client.post(url,{'page':'7','title':'جدید'})
        self.assertTrue(first.json()['created'])
        self.assertFalse(second.json()['created'])
        self.assertEqual(self.book.bookmark_set.filter(user=self.user,page=7).count(),1)
        self.assertEqual(self.book.bookmark_set.get(user=self.user,page=7).title,'جدید')


    def test_note_page_is_bounded(self):
        response=self.client.post(reverse('reader_note',args=[self.book.pk]),{'page':'999999999','text':'note'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['page'],1000000)


    def test_bookmark_get_is_not_allowed(self):
        response=self.client.get(reverse('reader_bookmark',args=[self.book.pk]))
        self.assertEqual(response.status_code,405)

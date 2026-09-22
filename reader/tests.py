from django.test import TestCase
from accounts.models import User
from books.models import Author, Book, Chapter
from gamification.models import PointLedger, UserStreak
from shop.models import Entitlement, SubscriptionPlan, Subscription
from .models import ReadingProgress, Review, Bookmark, Highlight, Note
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta


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


    def test_note_get_is_not_allowed(self):
        response=self.client.get(reverse('reader_note',args=[self.book.pk]))
        self.assertEqual(response.status_code,405)


    def test_progress_does_not_reduce_accumulated_time(self):
        url=reverse('reader_progress',args=[self.book.pk])
        self.client.post(url,{'progress':'30','seconds':'300','audio_seconds':'120'})
        self.client.post(url,{'progress':'40','seconds':'10','audio_seconds':'5'})
        saved=ReadingProgress.objects.get(user=self.user,book=self.book)
        self.assertEqual(saved.seconds,300)
        self.assertEqual(saved.audio_seconds,120)


    def test_replayed_progress_does_not_award_extra_study_activity(self):
        url=reverse('reader_progress',args=[self.book.pk])
        self.client.post(url,{'progress':'20','seconds':'120'})
        ledger_count=PointLedger.objects.filter(user=self.user).count()
        self.client.post(url,{'progress':'25','seconds':'120'})
        self.assertEqual(PointLedger.objects.filter(user=self.user).count(),ledger_count)


    def test_stale_progress_update_does_not_move_reader_backwards(self):
        url=reverse('reader_progress',args=[self.book.pk])
        self.client.post(url,{'progress':'70','page':'70'})
        self.client.post(url,{'progress':'20','page':'20'})
        saved=ReadingProgress.objects.get(user=self.user,book=self.book)
        self.assertEqual(float(saved.progress),70.0)
        self.assertEqual(saved.current_page,70)


    def test_stale_chapter_update_does_not_move_backwards(self):
        first=Chapter.objects.create(book=self.book,title='One',order=1)
        second=Chapter.objects.create(book=self.book,title='Two',order=2)
        url=reverse('reader_progress',args=[self.book.pk])
        self.client.post(url,{'progress':'60','chapter_id':second.pk})
        self.client.post(url,{'progress':'20','chapter_id':first.pk})
        saved=ReadingProgress.objects.get(user=self.user,book=self.book)
        self.assertEqual(saved.current_chapter_id,second.pk)


class SubscriptionReaderAccessTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='subscription-reader',password='pass12345')
        author=Author.objects.create(name='Subscription Test Author')
        self.book=Book.objects.create(name='Subscription Test Book',slug='subscription-test-book',author=author,status='published',visibility='public')
        self.client.force_login(self.user)

    def test_active_catalog_subscription_can_open_private_reader(self):
        user=User.objects.create_user(username='sub-reader',password='pass12345')
        author=Author.objects.create(name='Sub Reader Author')
        book=Book.objects.create(name='Sub Reader Book',slug='sub-reader-book',author=author,status='published',visibility='private')
        plan=SubscriptionPlan.objects.create(name='Reader Catalog',slug='reader-catalog',price=100,duration_days=30,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=5))
        self.client.login(username='sub-reader',password='pass12345')
        response=self.client.get(reverse('reader',args=[book.pk]))
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.context['accessible'])


    def test_bookmark_delete_is_scoped_to_current_user_and_book(self):
        item=Bookmark.objects.create(user=self.user,book=self.book,page=3,title='remove')
        response=self.client.post(reverse('reader_delete_bookmark',args=[self.book.pk,item.pk]))
        self.assertEqual(response.status_code,200)
        self.assertFalse(Bookmark.objects.filter(pk=item.pk).exists())

    def test_note_delete_cannot_delete_another_users_note(self):
        other=User.objects.create_user(username='note-owner',password='pass12345')
        item=Note.objects.create(user=other,book=self.book,page=2,text='private')
        response=self.client.post(reverse('reader_delete_note',args=[self.book.pk,item.pk]))
        self.assertEqual(response.status_code,404)
        self.assertTrue(Note.objects.filter(pk=item.pk).exists())


    def test_reader_can_search_own_notes(self):
        Note.objects.create(user=self.user,book=self.book,page=1,text='یادداشت مهم')
        Note.objects.create(user=self.user,book=self.book,page=2,text='متن دیگر')
        response=self.client.get(reverse('reader',args=[self.book.pk]),{'note_q':'مهم'})
        self.assertContains(response,'یادداشت مهم')
        self.assertNotContains(response,'متن دیگر')


    def test_highlight_requires_access_and_is_saved(self):
        response=self.client.post(reverse('reader_highlight',args=[self.book.pk]),{'page':'4','text':'بخش مهم'})
        self.assertEqual(response.status_code,200)
        self.assertTrue(Highlight.objects.filter(user=self.user,book=self.book,page=4,text='بخش مهم').exists())


    def test_duplicate_highlight_is_idempotent(self):
        url=reverse('reader_highlight',args=[self.book.pk])
        payload={'page':'5','text':'تکراری'}
        self.client.post(url,payload)
        response=self.client.post(url,payload)
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.json()['created'])
        self.assertEqual(Highlight.objects.filter(user=self.user,book=self.book,page=5,text='تکراری').count(),1)


    def test_highlight_delete_is_user_scoped(self):
        item=Highlight.objects.create(user=self.user,book=self.book,page=8,text='حذف من')
        response=self.client.post(reverse('reader_delete_highlight',args=[self.book.pk,item.pk]))
        self.assertEqual(response.status_code,200)
        self.assertFalse(Highlight.objects.filter(pk=item.pk).exists())


    def test_duplicate_note_is_idempotent(self):
        url=reverse('reader_note',args=[self.book.pk])
        payload={'page':'6','text':'یادداشت تکراری'}
        self.client.post(url,payload)
        response=self.client.post(url,payload)
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.json()['created'])
        self.assertEqual(Note.objects.filter(user=self.user,book=self.book,page=6,text='یادداشت تکراری').count(),1)


    def test_reader_can_search_highlights(self):
        Highlight.objects.create(user=self.user,book=self.book,page=1,text='عبارت مهم')
        Highlight.objects.create(user=self.user,book=self.book,page=2,text='عبارت دیگر')
        response=self.client.get(reverse('reader',args=[self.book.pk]),{'highlight_q':'مهم'})
        self.assertContains(response,'عبارت مهم')
        self.assertNotContains(response,'عبارت دیگر')


    def test_reader_page_is_not_cacheable(self):
        response=self.client.get(reverse('reader',args=[self.book.pk]))
        self.assertIn('no-cache',response.get('Cache-Control',''))
        self.assertIn('private',response.get('Cache-Control',''))


    def test_inactive_subscription_plan_cannot_open_private_reader(self):
        user=User.objects.create_user(username='inactive-plan-reader',password='pass12345')
        author=Author.objects.create(name='Inactive Plan Author')
        book=Book.objects.create(name='Inactive Plan Book',slug='inactive-plan-book',author=author,status='published',visibility='private')
        plan=SubscriptionPlan.objects.create(name='Inactive Catalog',slug='inactive-catalog',price=100,duration_days=30,grants_catalog_access=True,active=False)
        Subscription.objects.create(user=user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=5))
        self.client.login(username='inactive-plan-reader',password='pass12345')
        response=self.client.get(reverse('reader',args=[book.pk]))
        self.assertEqual(response.status_code,403)


    def test_private_reader_without_entitlement_returns_forbidden(self):
        author=Author.objects.create(name='Private Reader Author')
        book=Book.objects.create(name='Private Reader Book',slug='private-reader-book',author=author,status='published',visibility='private')
        response=self.client.get(reverse('reader',args=[book.pk]))
        self.assertEqual(response.status_code,403)

from django.test import TestCase
from accounts.models import User
from books.models import Author, Book, Chapter
from gamification.models import PointLedger, UserStreak
from shop.models import Entitlement, Subscription, SubscriptionPlan, SubscriptionPlan, Subscription
from .models import ReadingProgress, AudioProgress, Review, Bookmark, Highlight, Note, ProblemReport, SavedWord
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile


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
        self.book=Book.objects.create(name='Subscription Test Book',slug='subscription-test-book',author=author,status='published',visibility='public',subscription_included=True)
        self.client.force_login(self.user)

    def test_active_catalog_subscription_can_open_private_reader(self):
        user=User.objects.create_user(username='sub-reader',password='pass12345')
        author=Author.objects.create(name='Sub Reader Author')
        book=Book.objects.create(name='Sub Reader Book',slug='sub-reader-book',author=author,status='published',visibility='private',subscription_included=True)
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


    def test_paid_public_book_still_requires_entitlement(self):
        self.book.price=1000
        self.book.visibility='public'
        self.book.save(update_fields=['price','visibility'])
        response=self.client.get(reverse('reader',args=[self.book.pk]))
        self.assertEqual(response.status_code,403)

    def test_paid_public_book_allows_entitled_reader(self):
        self.book.price=1000
        self.book.visibility='public'
        self.book.save(update_fields=['price','visibility'])
        Entitlement.objects.create(user=self.user,book=self.book,source='purchase')
        response=self.client.get(reverse('reader',args=[self.book.pk]))
        self.assertEqual(response.status_code,200)


    def test_subscription_cannot_open_non_catalog_private_book(self):
        user=User.objects.create_user(username='scoped-sub-reader',password='pass12345')
        author=Author.objects.create(name='Scoped Reader Author')
        book=Book.objects.create(name='Not In Catalog',slug='not-in-catalog',author=author,status='published',visibility='private',subscription_included=False)
        plan=SubscriptionPlan.objects.create(name='Scoped Reader Plan',slug='scoped-reader-plan',price=0,duration_days=30,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=5))
        self.client.force_login(user)
        response=self.client.get(reverse('reader',args=[book.pk]))
        self.assertEqual(response.status_code,403)


    def test_subscription_access_is_not_reported_as_owned(self):
        plan=SubscriptionPlan.objects.create(name='Not owned',slug='not-owned',price=0,duration_days=7,grants_catalog_access=True)
        Subscription.objects.create(user=self.user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=2))
        self.book.visibility='private'
        self.book.subscription_included=True
        self.book.save(update_fields=['visibility','subscription_included'])
        response=self.client.get(reverse('reader',args=[self.book.pk]))
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.context['owned'])


    def test_reader_response_is_private_and_noindex(self):
        response=self.client.get(reverse('reader',args=[self.book.pk]))
        self.assertEqual(response.status_code,200)
        self.assertIn('private',response['Cache-Control'])
        self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(response['X-Robots-Tag'],'noindex, nofollow')
        self.assertEqual(response['Referrer-Policy'],'same-origin')


    def test_progress_response_is_not_cacheable(self):
        response=self.client.post(reverse('reader_progress',args=[self.book.pk]),{'progress':'10','page':'1'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response['Cache-Control'],'no-store')


    def test_reader_access_denied_response_is_private(self):
        private=Book.objects.create(name='Denied private',slug='denied-private',author=self.book.author,status='published',visibility='private')
        response=self.client.get(reverse('reader',args=[private.pk]))
        self.assertEqual(response.status_code,403)
        self.assertIn('private',response['Cache-Control'])
        self.assertIn('no-store',response['Cache-Control'])


    def test_vocabulary_response_is_private_and_noindex(self):
        response=self.client.get(reverse('reader_vocabulary'))
        self.assertEqual(response.status_code,200)
        self.assertIn('private',response['Cache-Control'])
        self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(response['X-Robots-Tag'],'noindex, nofollow')
        self.assertEqual(response['Referrer-Policy'],'same-origin')


class ReaderProblemReportTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='report-reader',password='pass12345')
        author=Author.objects.create(name='Report Author')
        self.book=Book.objects.create(name='Report Book',slug='report-book',author=author,price=0,status='published',visibility='public')
        self.client.force_login(self.user)

    def test_accessible_reader_can_report_problem(self):
        response=self.client.post(reverse('reader_report_problem',args=[self.book.pk]),{'text':'فایل صوتی مشکل دارد'})
        self.assertEqual(response.status_code,200)
        self.assertTrue(ProblemReport.objects.filter(user=self.user,book=self.book).exists())

    def test_empty_problem_report_is_rejected(self):
        response=self.client.post(reverse('reader_report_problem',args=[self.book.pk]),{'text':'   '})
        self.assertEqual(response.status_code,400)


    def test_problem_reports_are_rate_limited(self):
        for i in range(10):
            ProblemReport.objects.create(user=self.user,book=self.book,text=f'issue {i}')
        response=self.client.post(reverse('reader_report_problem',args=[self.book.pk]),{'text':'one more'})
        self.assertEqual(response.status_code,429)


class VocabularySearchTests(TestCase):
    def test_vocabulary_search_normalizes_persian_letters(self):
        user=User.objects.create_user(username='vocab-user',password='pass12345')
        SavedWord.objects.create(user=user,word='کتاب',normalized_word='کتاب')
        self.client.force_login(user)
        response=self.client.get(reverse('reader_vocabulary'),{'q':'كتاب'})
        self.assertContains(response,'کتاب')


    def test_saved_word_deduplicates_arabic_persian_variants(self):
        user=User.objects.create_user(username='word-dedupe',password='pass12345')
        article=__import__('articles.models',fromlist=['Article']).Article.objects.create(title='Word article',slug='word-article',published=True,abstract='text')
        self.client.force_login(user)
        url=reverse('reader_save_word',args=[article.slug])
        self.client.post(url,{'word':'كتاب'})
        self.client.post(url,{'word':'کتاب'})
        self.assertEqual(SavedWord.objects.filter(user=user).count(),1)


    def test_vocabulary_hides_words_linked_to_unpublished_articles(self):
        user=User.objects.create_user(username='private-vocab',password='pass12345')
        article=__import__('articles.models',fromlist=['Article']).Article.objects.create(title='Private article',slug='private-article',published=False,abstract='text')
        SavedWord.objects.create(user=user,word='secretword',normalized_word='secretword',article=article)
        self.client.force_login(user)
        response=self.client.get(reverse('reader_vocabulary'))
        self.assertNotContains(response,'secretword')


    def test_save_word_rejects_article_without_readable_content(self):
        user=User.objects.create_user(username='empty-article-word',password='pass12345')
        article=__import__('articles.models',fromlist=['Article']).Article.objects.create(title='Empty article',slug='empty-article',published=True)
        self.client.force_login(user)
        response=self.client.post(reverse('reader_save_word',args=[article.slug]),{'word':'test'})
        self.assertEqual(response.status_code,400)
        self.assertFalse(SavedWord.objects.filter(user=user).exists())



class RetiredSubscriptionPlanAccessTests(TestCase):
    def test_active_subscription_keeps_access_when_plan_is_retired(self):
        user=User.objects.create_user(username='subscriber-retired',password='pass12345')
        author=Author.objects.create(name='Sub Author')
        book=Book.objects.create(name='Subscription Book',slug='subscription-retired',author=author,status='published',price=100,subscription_included=True)
        plan=SubscriptionPlan.objects.create(name='Retired Plan',slug='retired-plan',price=10,duration_days=30,active=False,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,starts_at=timezone.now()-timezone.timedelta(days=1),expires_at=timezone.now()+timezone.timedelta(days=10),status='active')
        self.client.force_login(user)
        response=self.client.get(reverse('reader',args=[book.pk]))
        self.assertEqual(response.status_code,200)


class PasswordBookAccessTests(TestCase):
    def test_password_book_is_not_opened_without_unlock_flow(self):
        user=User.objects.create_user(username='password-reader',password='pass12345')
        author=Author.objects.create(name='Password Reader Author')
        book=Book.objects.create(name='Locked Book',slug='locked-book',author=author,status='published',visibility='password',access_password='secret',price=0)
        self.client.force_login(user)
        response=self.client.get(reverse('reader',args=[book.pk]))
        self.assertEqual(response.status_code,403)


class AudiobookExperienceTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='audio-user',password='pass12345')
        author=Author.objects.create(name='Audio Author')
        self.book=Book.objects.create(name='Audio Book',slug='audio-book',author=author,status='published',visibility='private',audio=SimpleUploadedFile('book.mp3',b'ID3audio',content_type='audio/mpeg'))
        self.chapter=Chapter.objects.create(book=self.book,title='فصل یک',order=1,audio=SimpleUploadedFile('chapter.mp3',b'ID3chapter',content_type='audio/mpeg'))
        self.client.force_login(self.user)

    def test_audio_player_requires_entitlement(self):
        self.assertEqual(self.client.get(reverse('audio_player',args=[self.book.pk])).status_code,403)
        Entitlement.objects.create(user=self.user,book=self.book,source='purchase')
        self.assertEqual(self.client.get(reverse('audio_player',args=[self.book.pk])).status_code,200)

    def test_secure_audio_denies_cross_book_access(self):
        other=Book.objects.create(name='Other Audio',slug='other-audio',author=self.book.author,status='published',visibility='private')
        foreign=Chapter.objects.create(book=other,title='Foreign',order=1,audio=SimpleUploadedFile('foreign.mp3',b'ID3foreign',content_type='audio/mpeg'))
        Entitlement.objects.create(user=self.user,book=self.book,source='purchase')
        response=self.client.get(reverse('chapter_secure_audio',args=[self.book.pk,foreign.pk]))
        self.assertEqual(response.status_code,404)

    def test_audio_progress_persists_per_chapter(self):
        Entitlement.objects.create(user=self.user,book=self.book,source='purchase')
        response=self.client.post(reverse('audio_progress',args=[self.book.pk]),{'chapter_id':self.chapter.pk,'position':'75','duration':'300'})
        self.assertEqual(response.status_code,200)
        item=AudioProgress.objects.get(user=self.user,book=self.book,chapter=self.chapter)
        self.assertEqual(item.position_seconds,75)
        self.assertFalse(item.completed)

    def test_expired_entitlement_cannot_save_audio_progress(self):
        Entitlement.objects.create(user=self.user,book=self.book,source='purchase',expires_at=timezone.now()-timedelta(seconds=1))
        response=self.client.post(reverse('audio_progress',args=[self.book.pk]),{'chapter_id':self.chapter.pk,'position':'20','duration':'100'})
        self.assertEqual(response.status_code,403)
        self.assertFalse(AudioProgress.objects.filter(user=self.user,book=self.book).exists())

    def test_audio_progress_rejects_chapter_from_other_book(self):
        other=Book.objects.create(name='Other',slug='audio-other',author=self.book.author,status='published')
        foreign=Chapter.objects.create(book=other,title='Other chapter',order=1)
        Entitlement.objects.create(user=self.user,book=self.book,source='purchase')
        response=self.client.post(reverse('audio_progress',args=[self.book.pk]),{'chapter_id':foreign.pk,'position':'10','duration':'100'})
        self.assertEqual(response.status_code,400)


    def test_expired_subscription_cannot_stream_audio(self):
        plan=SubscriptionPlan.objects.create(name='Audio plan',slug='audio-plan',price=10,duration_days=30,grants_catalog_access=True)
        self.book.subscription_included=True
        self.book.save(update_fields=['subscription_included'])
        Subscription.objects.create(user=self.user,plan=plan,starts_at=timezone.now()-timedelta(days=30),expires_at=timezone.now()-timedelta(seconds=1))
        response=self.client.get(reverse('book_secure_file',args=[self.book.pk,'audio']))
        self.assertEqual(response.status_code,403)

    def test_whole_book_audio_progress_is_idempotent(self):
        Entitlement.objects.create(user=self.user,book=self.book,source='purchase')
        url=reverse('audio_progress',args=[self.book.pk])
        self.client.post(url,{'position':'10','duration':'100'})
        self.client.post(url,{'position':'20','duration':'100'})
        self.assertEqual(AudioProgress.objects.filter(user=self.user,book=self.book,chapter__isnull=True).count(),1)
        self.assertEqual(AudioProgress.objects.get(user=self.user,book=self.book,chapter__isnull=True).position_seconds,20)


    def test_completed_whole_audiobook_marks_book_completed(self):
        Entitlement.objects.create(user=self.user,book=self.book,source='purchase')
        self.client.post(reverse('audio_progress',args=[self.book.pk]),{'position':'100','duration':'100'})
        progress=ReadingProgress.objects.get(user=self.user,book=self.book)
        self.assertEqual(float(progress.progress),100.0)

    def test_all_audio_chapters_completed_marks_book_completed(self):
        second=Chapter.objects.create(book=self.book,title='فصل دو',order=2,audio=SimpleUploadedFile('chapter2.mp3',b'ID3chapter2',content_type='audio/mpeg'))
        Entitlement.objects.create(user=self.user,book=self.book,source='purchase')
        url=reverse('audio_progress',args=[self.book.pk])
        self.client.post(url,{'chapter_id':self.chapter.pk,'position':'100','duration':'100'})
        self.assertLess(float(ReadingProgress.objects.get(user=self.user,book=self.book).progress),100)
        self.client.post(url,{'chapter_id':second.pk,'position':'100','duration':'100'})
        self.assertEqual(float(ReadingProgress.objects.get(user=self.user,book=self.book).progress),100.0)


class NativeChapterReaderTests(TestCase):
    def test_reader_renders_chapter_text_when_pdf_missing(self):
        user=User.objects.create_user(username='native-reader',password='pass12345')
        author=Author.objects.create(name='Native Author')
        book=Book.objects.create(name='Native Book',slug='native-book',author=author,status='published',visibility='public',price=0)
        Chapter.objects.create(book=book,title='فصل متنی',order=1,text='این متن واقعی فصل است.')
        self.client.force_login(user)
        response=self.client.get(reverse('reader',args=[book.pk]))
        self.assertContains(response,'فصل متنی')
        self.assertContains(response,'این متن واقعی فصل است.')
        self.assertContains(response,'فهرست فصل‌ها')

    def test_reader_does_not_expose_empty_chapters_in_native_toc(self):
        user=User.objects.create_user(username='native-empty',password='pass12345')
        author=Author.objects.create(name='Native Empty Author')
        book=Book.objects.create(name='Native Empty',slug='native-empty',author=author,status='published',visibility='public',price=0)
        Chapter.objects.create(book=book,title='خالی',order=1,text='')
        Chapter.objects.create(book=book,title='دارای متن',order=2,text='محتوا')
        self.client.force_login(user)
        response=self.client.get(reverse('reader',args=[book.pk]))
        self.assertNotContains(response,'خالی')
        self.assertContains(response,'دارای متن')



class AudioProgressMonotonicTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='audio-monotonic',password='pass12345')
        author=Author.objects.create(name='Audio Monotonic Author')
        self.book=Book.objects.create(name='Audio Monotonic',slug='audio-monotonic',author=author,status='published')
        self.chapter=Chapter.objects.create(book=self.book,title='فصل صوتی',order=1,audio=SimpleUploadedFile('mono.mp3',b'ID3mono',content_type='audio/mpeg'))
        self.client.force_login(self.user)

    def test_audio_progress_does_not_move_backwards(self):
        Entitlement.objects.create(user=self.user,book=self.book,source='purchase')
        url=reverse('audio_progress',args=[self.book.pk])
        self.client.post(url,{'chapter_id':self.chapter.pk,'position':'90','duration':'300'})
        self.client.post(url,{'chapter_id':self.chapter.pk,'position':'20','duration':'300'})
        item=AudioProgress.objects.get(user=self.user,book=self.book,chapter=self.chapter)
        self.assertEqual(item.position_seconds,90)

    def test_completed_audio_progress_stays_completed(self):
        Entitlement.objects.create(user=self.user,book=self.book,source='purchase')
        url=reverse('audio_progress',args=[self.book.pk])
        self.client.post(url,{'chapter_id':self.chapter.pk,'position':'100','duration':'100'})
        self.client.post(url,{'chapter_id':self.chapter.pk,'position':'10','duration':'100'})
        self.assertTrue(AudioProgress.objects.get(user=self.user,book=self.book,chapter=self.chapter).completed)



class AudioResumeCursorTests(TestCase):
    def setUp(self):
        from accounts.models import User
        from books.models import Author, Book
        from shop.models import Entitlement
        self.user=User.objects.create_user(username='audio-cursor',password='pass12345')
        author=Author.objects.create(name='Audio Cursor Author')
        self.book=Book.objects.create(name='Audio Cursor Book',slug='audio-cursor-book',author=author,status='published')
        Entitlement.objects.create(user=self.user,book=self.book)
        self.client.force_login(self.user)

    def test_backward_seek_becomes_saved_resume_position(self):
        from .models import AudioProgress
        progress=AudioProgress.objects.create(user=self.user,book=self.book,position_seconds=120,duration_seconds=300)
        response=self.client.post(reverse('audio_progress',args=[self.book.pk]),{'position':'45','duration':'300'})
        self.assertEqual(response.status_code,200)
        progress.refresh_from_db()
        self.assertEqual(progress.position_seconds,45)
        self.assertFalse(progress.completed)


class AudioStudyTimeIntegrityTests(TestCase):
    def test_audio_resume_cursor_does_not_inflate_reading_time(self):
        user=User.objects.create_user(username='audio-time-integrity',password='pass12345')
        author=Author.objects.create(name='Audio Time Author')
        book=Book.objects.create(name='Audio Time Book',slug='audio-time-book',author=author,status='published',visibility='public',price=0)
        book.audio=SimpleUploadedFile('audio-time.mp3',b'audio',content_type='audio/mpeg')
        book.save(update_fields=['audio'])
        self.client.force_login(user)
        response=self.client.post(reverse('audio_progress',args=[book.pk]),{'position':'1800','duration':'3600'})
        self.assertEqual(response.status_code,200)
        aggregate=ReadingProgress.objects.get(user=user,book=book)
        self.assertEqual(aggregate.audio_seconds,0)
        self.assertFalse(UserStreak.objects.filter(user=user).exists())


class ReaderResumeCursorTests(TestCase):
    def test_reader_resume_cursor_can_move_to_earlier_chapter(self):
        user=User.objects.create_user(username='reader-cursor',password='pass12345')
        author=Author.objects.create(name='Reader Cursor Author')
        book=Book.objects.create(name='Reader Cursor Book',slug='reader-cursor-book',author=author,status='published',visibility='public',price=0)
        first=Chapter.objects.create(book=book,title='First',order=1,text='one')
        second=Chapter.objects.create(book=book,title='Second',order=2,text='two')
        ReadingProgress.objects.create(user=user,book=book,progress=80,current_page=2,current_chapter=second,seconds=100)
        self.client.force_login(user)
        response=self.client.post(reverse('reader_progress',args=[book.pk]),{'progress':'50','page':'1','chapter_id':first.pk,'seconds':'120'})
        self.assertEqual(response.status_code,200)
        saved=ReadingProgress.objects.get(user=user,book=book)
        self.assertEqual(saved.current_chapter_id,first.pk)
        self.assertEqual(saved.current_page,1)
        self.assertEqual(float(saved.progress),80)
        self.assertEqual(saved.seconds,120)

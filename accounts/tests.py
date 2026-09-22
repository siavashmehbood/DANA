from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.hashers import make_password, check_password

from .models import OTPCode, User
from shop.models import Referral, Entitlement, SubscriptionPlan, Subscription
from books.models import Author, Book


class AccountFlowTests(TestCase):
    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, f'{reverse("login")}?next={reverse("profile")}')

    def test_otp_login_creates_referral_without_crashing(self):
        inviter = User.objects.create_user(username='inviter', password='pass123')
        session = self.client.session
        session['otp_phone'] = '+989121234567'
        session['referral_code'] = inviter.referral_code
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        OTPCode.objects.create(
            phone='+989121234567',
            code=make_password('12345'),
            purpose='login',
            expires_at=timezone.now() + timedelta(minutes=2),
        )

        response = self.client.post(reverse('otp'), {'code': '12345'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        invitee = User.objects.get(phone='+989121234567')
        self.assertTrue(Referral.objects.filter(inviter=inviter, invitee=invitee).exists())


    def test_library_excludes_expired_entitlements(self):
        user = User.objects.create_user(username='library-user', password='pass12345')
        author = Author.objects.create(name='Library Author')
        active = Book.objects.create(name='Active Access', slug='active-access', author=author, status='published')
        expired = Book.objects.create(name='Expired Access', slug='expired-access', author=author, status='published')
        Entitlement.objects.create(user=user, book=active)
        Entitlement.objects.create(user=user, book=expired, expires_at=timezone.now()-timedelta(minutes=1))
        self.client.force_login(user)
        response = self.client.get(reverse('library'))
        self.assertContains(response, 'Active Access')
        self.assertNotContains(response, 'Expired Access')


    def test_profile_rejects_disguised_avatar_extension(self):
        user=User.objects.create_user(username='avatar-user',password='pass12345')
        self.client.force_login(user)
        bad=SimpleUploadedFile('avatar.exe',b'not-an-image',content_type='image/png')
        response=self.client.post(reverse('profile'),{'avatar':bad})
        self.assertRedirects(response,reverse('profile'))
        user.refresh_from_db()
        self.assertFalse(bool(user.avatar))


class LibraryFilterTests(TestCase):
    def test_invalid_library_filters_fall_back_to_all(self):
        user=User.objects.create_user(username='library-filter',password='pass12345')
        self.client.force_login(user)
        response=self.client.get(reverse('library'),{'state':'bad','kind':'bad'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['state'],'all')
        self.assertEqual(response.context['kind'],'all')


    def test_library_hides_draft_entitlement(self):
        from books.models import Author, Book
        from shop.models import Entitlement
        user=User.objects.create_user(username='library-draft',password='pass12345')
        author=Author.objects.create(name='Draft Author')
        draft=Book.objects.create(name='Draft owned',slug='draft-owned',author=author,status='draft')
        Entitlement.objects.create(user=user,book=draft)
        self.client.force_login(user)
        response=self.client.get(reverse('library'))
        self.assertNotContains(response,'Draft owned')


    def test_library_includes_catalog_for_active_subscription(self):
        user=User.objects.create_user(username='subscriber-library',password='pass12345')
        author=Author.objects.create(name='Subscription Author')
        Book.objects.create(name='Subscription Book',slug='subscription-book',author=author,status='published',subscription_included=True)
        plan=SubscriptionPlan.objects.create(name='Catalog',slug='catalog-library',price=100,duration_days=30,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,status='active',starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=29))
        self.client.force_login(user)
        response=self.client.get(reverse('library'))
        self.assertContains(response,'Subscription Book')
        self.assertContains(response,'اشتراک')

    def test_library_excludes_catalog_for_expired_subscription(self):
        user=User.objects.create_user(username='expired-subscriber-library',password='pass12345')
        author=Author.objects.create(name='Expired Subscription Author')
        Book.objects.create(name='Expired Subscription Book',slug='expired-subscription-book',author=author,status='published')
        plan=SubscriptionPlan.objects.create(name='Expired Catalog',slug='expired-catalog-library',price=100,duration_days=30,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,status='expired',starts_at=timezone.now()-timedelta(days=31),expires_at=timezone.now()-timedelta(days=1))
        self.client.force_login(user)
        response=self.client.get(reverse('library'))
        self.assertNotContains(response,'Expired Subscription Book')


    def test_library_can_filter_subscription_access(self):
        user=User.objects.create_user(username='library-source',password='pass12345')
        author=Author.objects.create(name='Source Author')
        purchased=Book.objects.create(name='Purchased Only',slug='purchased-only',author=author,status='published')
        subscribed=Book.objects.create(name='Subscription Only',slug='subscription-only',author=author,status='published',subscription_included=True)
        Entitlement.objects.create(user=user,book=purchased)
        plan=SubscriptionPlan.objects.create(name='Source Plan',slug='source-plan',price=100,duration_days=30,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,status='active',starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=1))
        self.client.force_login(user)
        response=self.client.get(reverse('library'),{'source':'subscription'})
        self.assertContains(response,'Subscription Only')
        self.assertNotContains(response,'Purchased Only')


class SessionSecurityTests(TestCase):
    def test_logout_others_invalidates_django_sessions(self):
        user=User.objects.create_user(username='multi-session',password='pass12345')
        first=Client()
        second=Client()
        first.post(reverse('login'),{'login_method':'password','username':'multi-session','password':'pass12345'})
        second.post(reverse('login'),{'login_method':'password','username':'multi-session','password':'pass12345'})
        self.assertEqual(first.get(reverse('profile')).status_code,200)
        self.assertEqual(second.get(reverse('profile')).status_code,200)
        first.post(reverse('logout_others'))
        self.assertEqual(first.get(reverse('profile')).status_code,200)
        self.assertEqual(second.get(reverse('profile')).status_code,302)


class WalletIntegrityTests(TestCase):
    def test_model_validation_rejects_negative_wallet_balance(self):
        from django.core.exceptions import ValidationError
        user=User(username='negative-wallet',wallet_balance=-1)
        with self.assertRaises(ValidationError):
            user.full_clean()


class PasswordChangeSecurityTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='password-user',password='old-pass-123')
        self.client.login(username='password-user',password='old-pass-123')

    def test_password_change_requires_current_password(self):
        response=self.client.post(reverse('profile'),{'new_password':'new-pass-456'})
        self.assertEqual(response.status_code,302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('old-pass-123'))

    def test_password_change_accepts_correct_current_password(self):
        response=self.client.post(reverse('profile'),{'current_password':'old-pass-123','new_password':'new-pass-456'})
        self.assertEqual(response.status_code,200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('new-pass-456'))


class OtpStorageSecurityTests(TestCase):
    def test_generated_otp_is_not_stored_in_plaintext(self):
        response=self.client.post(reverse('login'),{'login_method':'otp','phone':'09121234567','terms':'1'})
        self.assertEqual(response.status_code,302)
        row=OTPCode.objects.latest('id')
        self.assertNotEqual(len(row.code),5)
        self.assertTrue(row.code.startswith(('pbkdf2_','argon2','bcrypt','scrypt')))


class DashboardSubscriptionTests(TestCase):
    def test_dashboard_counts_subscription_catalog_without_duplicates(self):
        user=User.objects.create_user(username='dashboard-sub',password='pass12345')
        author=Author.objects.create(name='Dashboard Author')
        book=Book.objects.create(name='Dashboard Book',slug='dashboard-book',author=author,status='published')
        Entitlement.objects.create(user=user,book=book)
        plan=SubscriptionPlan.objects.create(name='Dashboard Plan',slug='dashboard-plan',price=100,duration_days=30,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=5))
        self.client.force_login(user)
        response=self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['books_count'],1)


    def test_subscription_library_excludes_non_catalog_books(self):
        user=User.objects.create_user(username='catalog-scope',password='pass12345')
        author=Author.objects.create(name='Catalog Scope Author')
        Book.objects.create(name='Excluded Private',slug='excluded-private',author=author,status='published',visibility='private',subscription_included=False)
        plan=SubscriptionPlan.objects.create(name='Scoped Catalog',slug='scoped-catalog',price=0,duration_days=30,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,status='active',starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=10))
        self.client.force_login(user)
        response=self.client.get(reverse('library'))
        self.assertNotContains(response,'Excluded Private')


class LoginRedirectTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='next-user',password='pass12345')

    def test_password_login_returns_to_safe_local_destination(self):
        response=self.client.post(reverse('login'),{'login_method':'password','username':'next-user','password':'pass12345','next':'/shop/subscriptions/'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(response.url,'/shop/subscriptions/')

    def test_password_login_rejects_external_destination(self):
        response=self.client.post(reverse('login'),{'login_method':'password','username':'next-user','password':'pass12345','next':'https://evil.example/'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(response.url,'/')


class LibraryRecommendationTests(TestCase):
    def test_library_recommends_same_category_without_owned_book(self):
        from books.models import Author, Book, Category
        from shop.models import Entitlement
        user=User.objects.create_user(username='library-rec',password='pass12345')
        author=Author.objects.create(name='Library Rec Author')
        category=Category.objects.create(name='Library Rec',slug='library-rec')
        owned=Book.objects.create(name='Owned Rec',slug='owned-rec',author=author,category=category,status='published')
        candidate=Book.objects.create(name='Candidate Rec',slug='candidate-rec',author=author,category=category,status='published')
        Entitlement.objects.create(user=user,book=owned)
        self.client.force_login(user)
        response=self.client.get(reverse('library'))
        self.assertIn(candidate,list(response.context['recommended_books']))
        self.assertNotIn(owned,list(response.context['recommended_books']))


class ReadingProfileTests(TestCase):
    def test_profile_uses_real_streak_badges_and_recent_progress(self):
        from gamification.models import UserStreak, Badge, UserBadge
        from reader.models import ReadingProgress
        from books.models import Author, Book
        user=User.objects.create_user(username='reading-profile',password='pass12345')
        author=Author.objects.create(name='Profile Author')
        book=Book.objects.create(name='Profile Reading',slug='profile-reading',author=author,status='published')
        ReadingProgress.objects.create(user=user,book=book,progress=35)
        UserStreak.objects.create(user=user,current_days=4,longest_days=7)
        badge=Badge.objects.create(name='Reader Badge',active=True)
        UserBadge.objects.create(user=user,badge=badge)
        self.client.force_login(user)
        response=self.client.get(reverse('profile'))
        self.assertContains(response,'Profile Reading')
        self.assertContains(response,'Reader Badge')
        self.assertContains(response,'روزهای پیوسته')


class AudioLibraryStateTests(TestCase):
    def setUp(self):
        from books.models import Author, Book
        from shop.models import Entitlement
        self.user=User.objects.create_user(username='audio-library',password='pass12345')
        author=Author.objects.create(name='Audio Library Author')
        self.book=Book.objects.create(name='Audio Library Book',slug='audio-library-book',author=author,status='published')
        Entitlement.objects.create(user=self.user,book=self.book)
        self.client.force_login(self.user)

    def test_listening_only_book_appears_in_reading_filter(self):
        from reader.models import AudioProgress
        AudioProgress.objects.create(user=self.user,book=self.book,position_seconds=45,duration_seconds=300)
        response=self.client.get(reverse('library'),{'state':'reading'})
        self.assertContains(response,'Audio Library Book')

    def test_completed_audio_book_appears_in_completed_filter(self):
        from reader.models import AudioProgress
        AudioProgress.objects.create(user=self.user,book=self.book,position_seconds=300,duration_seconds=300,completed=True)
        response=self.client.get(reverse('library'),{'state':'completed'})
        self.assertContains(response,'Audio Library Book')


class RecommendationColdStartTests(TestCase):
    def test_empty_library_gets_popular_fallback_recommendations(self):
        from books.models import Author, Book
        user=User.objects.create_user(username='cold-rec',password='pass12345')
        author=Author.objects.create(name='Cold Author')
        candidate=Book.objects.create(name='Cold Candidate',slug='cold-candidate',author=author,status='published',visibility='public')
        self.client.force_login(user)
        response=self.client.get(reverse('library'))
        self.assertIn(candidate,list(response.context['recommended_books']))


    def test_library_keeps_access_for_retired_subscription_plan_until_expiry(self):
        user=User.objects.create_user(username='retired-plan-user',password='pass12345')
        author=Author.objects.create(name='Retired Plan Author')
        Book.objects.create(name='Retired Plan Book',slug='retired-plan-book',author=author,status='published',subscription_included=True)
        plan=SubscriptionPlan.objects.create(name='Retired Catalog',slug='retired-catalog',price=0,duration_days=30,grants_catalog_access=True,active=False)
        Subscription.objects.create(user=user,plan=plan,status='active',starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=5))
        self.client.force_login(user)
        response=self.client.get(reverse('library'))
        self.assertContains(response,'Retired Plan Book')

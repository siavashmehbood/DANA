from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

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
            code='12345',
            purpose='login',
            expires_at=timezone.now() + timedelta(minutes=2),
        )

        response = self.client.post(reverse('otp'), {'code': '12345'})

        self.assertRedirects(response, reverse('home'))
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
        Book.objects.create(name='Subscription Book',slug='subscription-book',author=author,status='published')
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
        subscribed=Book.objects.create(name='Subscription Only',slug='subscription-only',author=author,status='published')
        Entitlement.objects.create(user=user,book=purchased)
        plan=SubscriptionPlan.objects.create(name='Source Plan',slug='source-plan',price=100,duration_days=30,grants_catalog_access=True)
        Subscription.objects.create(user=user,plan=plan,status='active',starts_at=timezone.now()-timedelta(days=1),expires_at=timezone.now()+timedelta(days=1))
        self.client.force_login(user)
        response=self.client.get(reverse('library'),{'source':'subscription'})
        self.assertContains(response,'Subscription Only')
        self.assertNotContains(response,'Purchased Only')

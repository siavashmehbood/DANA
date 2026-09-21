from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from .models import OTPCode, User
from shop.models import Referral, Entitlement
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

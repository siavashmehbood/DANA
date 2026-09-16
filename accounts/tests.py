from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from .models import OTPCode, User
from shop.models import Referral


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

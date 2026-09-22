from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from books.models import Author, Book
from reader.models import ListeningActivity, ReadingActivity


class AnalyticsTruthTests(TestCase):
    def setUp(self):
        self.staff=User.objects.create_user(username='analytics-staff',password='pass12345',is_staff=True)
        self.client.force_login(self.staff)
        author=Author.objects.create(name='Analytics Author')
        self.book=Book.objects.create(name='Analytics Book',slug='analytics-book',author=author,status='published')

    def test_active_readers_include_text_and_audio_activity_without_double_counting_user(self):
        text_user=User.objects.create_user(username='analytics-text',password='pass12345')
        audio_user=User.objects.create_user(username='analytics-audio',password='pass12345')
        ReadingActivity.objects.create(user=text_user,book=self.book,seconds=60)
        ListeningActivity.objects.create(user=text_user,book=self.book,seconds=30)
        ListeningActivity.objects.create(user=audio_user,book=self.book,seconds=45)
        response=self.client.get(reverse('analytics'))
        self.assertEqual(response.context['active_readers'],2)

    def test_old_activity_is_not_counted_active(self):
        user=User.objects.create_user(username='analytics-old',password='pass12345')
        row=ReadingActivity.objects.create(user=user,book=self.book,seconds=60)
        ReadingActivity.objects.filter(pk=row.pk).update(created_at=timezone.now()-timedelta(days=31))
        response=self.client.get(reverse('analytics'))
        self.assertEqual(response.context['active_readers'],0)

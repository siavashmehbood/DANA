from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from .models import Notification

class NotificationTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='notify-user',password='pass12345')
        self.other=User.objects.create_user(username='notify-other',password='pass12345')
        self.mine=Notification.objects.create(user=self.user,title='Mine',body='Body')
        self.theirs=Notification.objects.create(user=self.other,title='Theirs',body='Body')
        self.client.force_login(self.user)
    def test_mark_read_is_owner_scoped(self):
        self.client.post(reverse('notification_mark_read',args=[self.theirs.pk]))
        self.theirs.refresh_from_db()
        self.assertIsNone(self.theirs.read_at)
        self.client.post(reverse('notification_mark_read',args=[self.mine.pk]))
        self.mine.refresh_from_db()
        self.assertIsNotNone(self.mine.read_at)
    def test_mark_all_only_updates_current_user(self):
        self.client.post(reverse('notifications_mark_all_read'))
        self.mine.refresh_from_db(); self.theirs.refresh_from_db()
        self.assertIsNotNone(self.mine.read_at)
        self.assertIsNone(self.theirs.read_at)

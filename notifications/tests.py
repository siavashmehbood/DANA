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

    def test_notifications_are_paginated_and_unread_count_is_global(self):
        for i in range(35):
            Notification.objects.create(user=self.user,title=f'N {i}',body='Body')
        response=self.client.get(reverse('notifications'))
        self.assertEqual(len(response.context['items']),30)
        self.assertEqual(response.context['unread_count'],36)
        second=self.client.get(reverse('notifications')+'?page=2')
        self.assertEqual(len(second.context['items']),6)

    def test_mark_read_preserves_current_page(self):
        response=self.client.post(reverse('notification_mark_read',args=[self.mine.pk]),{'page':'2'})
        self.assertRedirects(response,reverse('notifications')+'?page=2',fetch_redirect_response=False)

    def test_invalid_page_falls_back_to_first_page(self):
        response=self.client.get(reverse('notifications')+'?page=invalid')
        self.assertEqual(response.context['page_obj'].number,1)

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from books.models import Author, Book
from reader.models import ListeningActivity, ReadingActivity, ReadingProgress
from .models import PointLedger
from .services import add_points


class PointLedgerTests(TestCase):
    def test_reference_makes_award_idempotent(self):
        user=User.objects.create_user(username='points-user',password='pass12345')
        first=add_points(user,PointLedger.PURCHASE,2,'purchase',reference='order:42')
        second=add_points(user,PointLedger.PURCHASE,2,'purchase',reference='order:42')
        user.refresh_from_db()
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(PointLedger.objects.filter(reference='order:42').count(),1)
        self.assertEqual(user.purchase_points,2)


class LeaderboardActivityTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='leaderboard-user',password='pass12345',leaderboard_public=True)
        self.author=Author.objects.create(name='Telemetry Author')
        self.book=Book.objects.create(name='Telemetry Book',slug='telemetry-book',author=self.author,status='published')
        self.client.force_login(self.user)

    def _activity(self, model, seconds, age):
        row=model.objects.create(user=self.user,book=self.book,seconds=seconds)
        model.objects.filter(pk=row.pk).update(created_at=timezone.now()-age)
        return row

    def _value(self, period):
        response=self.client.get(reverse('leaderboard'),{'period':period,'metric':'study_hours'})
        self.assertEqual(response.status_code,200)
        return response.context['my_value']

    def test_old_activity_is_excluded_from_current_week(self):
        self._activity(ReadingActivity,3600,timedelta(days=8))
        self.assertEqual(self._value('week'),0)

    def test_recent_reading_activity_is_counted(self):
        self._activity(ReadingActivity,3600,timedelta(hours=1))
        self.assertEqual(self._value('week'),1.0)

    def test_listening_activity_is_counted(self):
        self._activity(ListeningActivity,1800,timedelta(hours=1))
        self.assertEqual(self._value('week'),0.5)

    def test_reading_and_listening_are_combined(self):
        self._activity(ReadingActivity,1800,timedelta(hours=1))
        self._activity(ListeningActivity,1800,timedelta(hours=1))
        self.assertEqual(self._value('week'),1.0)

    def test_week_month_and_year_use_independent_windows(self):
        self._activity(ReadingActivity,3600,timedelta(days=3))
        self._activity(ReadingActivity,7200,timedelta(days=15))
        self._activity(ListeningActivity,10800,timedelta(days=90))
        self._activity(ListeningActivity,14400,timedelta(days=400))
        self.assertEqual(self._value('week'),1.0)
        self.assertEqual(self._value('month'),3.0)
        self.assertEqual(self._value('year'),6.0)

    def test_progress_snapshot_does_not_inflate_study_hours(self):
        ReadingProgress.objects.create(user=self.user,book=self.book,seconds=36000,progress=50)
        self.assertEqual(self._value('week'),0)

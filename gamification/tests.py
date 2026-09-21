from django.test import TestCase
from accounts.models import User
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

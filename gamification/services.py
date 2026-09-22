from datetime import timedelta
from decimal import Decimal

from django.db import transaction, IntegrityError
from django.utils import timezone

from .models import XPEvent, PointLedger, UserStreak


@transaction.atomic
def add_xp(user, amount, reason, source=''):
    from accounts.models import User
    user = User.objects.select_for_update().get(pk=user.pk)
    amount = int(amount)
    if not amount:
        return
    user.xp = max(0, user.xp + amount)
    user.save(update_fields=['xp'])
    XPEvent.objects.create(user=user, amount=amount, reason=reason, source=source)


@transaction.atomic
def add_points(user, point_type, amount, reason, book=None, reference=''):
    from accounts.models import User
    user = User.objects.select_for_update().get(pk=user.pk)
    amount = Decimal(str(amount))
    if amount <= 0:
        return None
    if point_type == PointLedger.STUDY and book is not None:
        exists = PointLedger.objects.filter(
            user=user, point_type=PointLedger.STUDY, book=book,
            revoked=False,
        ).exists()
        if exists:
            return None
    if reference and PointLedger.objects.filter(reference=reference, revoked=False).exists():
        return None
    row = PointLedger.objects.create(
        user=user, point_type=point_type, amount=amount,
        reason=reason, book=book, reference=reference,
    )
    field = 'purchase_points' if point_type == PointLedger.PURCHASE else 'study_points'
    setattr(user, field, getattr(user, field) + amount)
    user.save(update_fields=[field])
    return row


@transaction.atomic
def record_study_activity(user):
    from accounts.models import User
    user = User.objects.select_for_update().get(pk=user.pk)
    today = timezone.localdate()
    streak, _ = UserStreak.objects.get_or_create(user=user)
    streak = UserStreak.objects.select_for_update().get(pk=streak.pk)
    if streak.last_activity_date == today:
        return streak
    if streak.last_activity_date == today - timedelta(days=1):
        streak.current_days += 1
    else:
        streak.current_days = 1
    streak.longest_days = max(streak.longest_days, streak.current_days)
    streak.last_activity_date = today
    streak.save(update_fields=['current_days', 'longest_days', 'last_activity_date'])
    return streak


def study_points_for_score(score):
    return Decimal(str(max(0, min(10, int(score))))) * Decimal('4')


def purchase_points_for_amount(amount):
    return Decimal(str(amount)) / Decimal('1000000')

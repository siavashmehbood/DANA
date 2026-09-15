from django.db import models
from accounts.models import User
from books.models import Book

class GamificationLevel(models.Model):
    name = models.CharField(max_length=80)
    min_xp = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    benefits = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'min_xp']

class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='badges/', blank=True, null=True)
    xp_reward = models.PositiveIntegerField(default=0)
    tier = models.CharField(max_length=20, default='bronze')
    active = models.BooleanField(default=True)

class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'badge'], name='unique_user_badge')]

class XPEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.IntegerField()
    reason = models.CharField(max_length=200)
    source = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class PointLedger(models.Model):
    PURCHASE = 'purchase'
    STUDY = 'study'
    TYPES = [(PURCHASE, 'خرید'), (STUDY, 'مطالعه')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_ledger')
    point_type = models.CharField(max_length=20, choices=TYPES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.CharField(max_length=250)
    book = models.ForeignKey(Book, null=True, blank=True, on_delete=models.SET_NULL)
    reference = models.CharField(max_length=100, blank=True)
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Mission(models.Model):
    PERIODS = [('daily', 'روزانه'), ('weekly', 'هفتگی'), ('monthly', 'ماهانه')]
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    period = models.CharField(max_length=20, choices=PERIODS)
    target = models.PositiveIntegerField(default=1)
    xp_reward = models.PositiveIntegerField(default=0)
    study_points_reward = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    active = models.BooleanField(default=True)

class UserMission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    progress = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    period_key = models.CharField(max_length=20)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'mission', 'period_key'], name='unique_user_mission_period')]

class UserStreak(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='streak')
    current_days = models.PositiveIntegerField(default=0)
    longest_days = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)

class HallOfFameRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=50)
    value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    period = models.CharField(max_length=20, default='all')
    created_at = models.DateTimeField(auto_now_add=True)

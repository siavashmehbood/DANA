from django.db import models
from accounts.models import User

class Ticket(models.Model):
    STATUS = [('open', 'باز'), ('in_progress', 'در حال بررسی'), ('waiting', 'منتظر پاسخ'), ('resolved', 'حل‌شده'), ('closed', 'بسته')]
    PRIORITIES = [('low', 'کم'), ('normal', 'عادی'), ('high', 'زیاد'), ('urgent', 'فوری')]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=250)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITIES, default='normal')
    category = models.CharField(max_length=80, blank=True)
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['user','-updated_at'], name='support_user_updated_idx'), models.Index(fields=['status','priority','-updated_at'], name='support_queue_idx')]

class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

from django.db import models
from accounts.models import User

class Ticket(models.Model):
    STATUS = [('open', 'Open'), ('in_progress', 'In Progress'), ('waiting', 'Waiting'), ('resolved', 'Resolved'), ('closed', 'Closed')]
    PRIORITIES = [('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=250)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITIES, default='normal')
    category = models.CharField(max_length=80, blank=True)
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

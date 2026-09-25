from django.db import models
from accounts.models import User

class Notification(models.Model):
    KIND=[('info','اطلاع'),('success','موفقیت'),('warning','هشدار')]
    user=models.ForeignKey(User,null=True,blank=True,on_delete=models.CASCADE,related_name='notifications')
    title=models.CharField(max_length=200)
    body=models.TextField()
    kind=models.CharField(max_length=20,choices=KIND,default='info')
    read_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes=[models.Index(fields=['user','-created_at'],name='notify_user_created_idx'),models.Index(fields=['user','read_at'],name='notify_user_read_idx')]

class PushSubscription(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    endpoint=models.TextField(unique=True)
    p256dh=models.TextField(blank=True)
    auth=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

class EmailLog(models.Model):
    user=models.ForeignKey(User,null=True,blank=True,on_delete=models.SET_NULL)
    email=models.EmailField()
    subject=models.CharField(max_length=250)
    status=models.CharField(max_length=30,default='queued')
    created_at=models.DateTimeField(auto_now_add=True)

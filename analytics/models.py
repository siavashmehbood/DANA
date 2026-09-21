from django.db import models
from accounts.models import User
from books.models import Book

class Event(models.Model):
    user=models.ForeignKey(User,null=True,blank=True,on_delete=models.SET_NULL)
    book=models.ForeignKey(Book,null=True,blank=True,on_delete=models.SET_NULL)
    name=models.CharField(max_length=80)
    value=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    metadata=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes=[
            models.Index(fields=['name','created_at']),
            models.Index(fields=['user','created_at']),
        ]

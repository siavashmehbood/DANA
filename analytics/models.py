from django.db import models
from accounts.models import User
from books.models import Book

class Event(models.Model):
    user=models.ForeignKey(User,null=True,blank=True,on_delete=models.SET_NULL)
    book=models.ForeignKey(Book,null=True,blank=True,on_delete=models.SET_NULL)
    name=models.CharField(max_length=80)
    value=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    metadata=models.JSONField(default=dict,blank=True)
    session_key=models.CharField(max_length=64,blank=True,db_index=True,editable=False)
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes=[
            models.Index(fields=['name','created_at'], name='analytics_e_name_6ca12c_idx'),
            models.Index(fields=['user','created_at'], name='analytics_e_user_id_9a87e5_idx'),
        ]

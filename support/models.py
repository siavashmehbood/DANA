from django.db import models
from accounts.models import User
class Ticket(models.Model): STATUS=[('open','باز'),('pending','در انتظار'),('closed','بسته')]; user=models.ForeignKey(User,on_delete=models.CASCADE); subject=models.CharField(max_length=250); body=models.TextField(); status=models.CharField(max_length=20,choices=STATUS,default='open'); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
class TicketMessage(models.Model): ticket=models.ForeignKey(Ticket,on_delete=models.CASCADE,related_name='messages'); user=models.ForeignKey(User,on_delete=models.CASCADE); body=models.TextField(); created_at=models.DateTimeField(auto_now_add=True)

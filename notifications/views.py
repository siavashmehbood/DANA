from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Notification
@login_required
def notifications(request): return render(request,'notifications/list.html',{'items':Notification.objects.filter(user=request.user).order_by('-created_at')})

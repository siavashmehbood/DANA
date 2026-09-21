from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Notification

@login_required
def notifications(request):
    return render(request,'notifications/list.html',{'items':Notification.objects.filter(user=request.user).order_by('-created_at')})

@login_required
@require_POST
def mark_read(request, pk):
    Notification.objects.filter(pk=pk, user=request.user, read_at__isnull=True).update(read_at=timezone.now())
    return redirect('notifications')

@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=timezone.now())
    return redirect('notifications')

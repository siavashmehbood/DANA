from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from .models import Notification

@login_required
def notifications(request):
    qs=Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count=qs.filter(read_at__isnull=True).count()
    page_obj=Paginator(qs,30).get_page(request.GET.get('page'))
    return render(request,'notifications/list.html',{'items':page_obj.object_list,'page_obj':page_obj,'unread_count':unread_count})

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

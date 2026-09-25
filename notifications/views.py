from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache
from .models import Notification

@login_required
@never_cache
def notifications(request):
    qs=Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count=qs.filter(read_at__isnull=True).count()
    raw_page=(request.GET.get('page') or '1')[:12]
    page_obj=Paginator(qs,30).get_page(raw_page if raw_page.isdigit() and int(raw_page)>0 else '1')
    return render(request,'notifications/list.html',{'items':page_obj.object_list,'page_obj':page_obj,'unread_count':unread_count})

@login_required
@require_POST
def mark_read(request, pk):
    Notification.objects.filter(pk=pk, user=request.user, read_at__isnull=True).update(read_at=timezone.now())
    next_page=(request.POST.get('page') or '').strip()
    return redirect(f"{reverse('notifications')}?page={next_page}" if next_page.isdigit() and int(next_page)>1 else 'notifications')

@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=timezone.now())
    return redirect('notifications')

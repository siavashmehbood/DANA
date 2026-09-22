from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache
from .models import Ticket, TicketMessage

@login_required
@never_cache
def tickets(request):
    if request.method == 'POST':
        subject = request.POST.get('subject','').strip()[:250]
        body = request.POST.get('body','').strip()[:10000]
        if not subject or not body:
            messages.error(request, 'موضوع و متن درخواست پشتیبانی الزامی است.')
            return redirect('tickets')
        if Ticket.objects.filter(user=request.user,subject=subject,status__in=['open','waiting','in_progress']).exists():
            messages.error(request, 'یک درخواست باز با همین موضوع دارید.')
            return redirect('tickets')
        Ticket.objects.create(user=request.user, subject=subject, body=body)
        messages.success(request, 'درخواست پشتیبانی ثبت شد.')
        return redirect('tickets')
    qs=Ticket.objects.filter(user=request.user).prefetch_related('messages__user').order_by('-updated_at')
    page_obj=Paginator(qs,20).get_page(request.GET.get('page'))
    return render(request,'support/tickets.html',{'tickets':page_obj.object_list,'page_obj':page_obj})


@login_required
@require_POST
def reply_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, user=request.user)
    if ticket.status in {'closed','resolved'}:
        messages.error(request, 'این درخواست بسته یا حل شده است.')
        return redirect('tickets')
    body = request.POST.get('body','').strip()[:10000]
    if not body:
        messages.error(request, 'متن پاسخ نمی‌تواند خالی باشد.')
        return redirect('tickets')
    TicketMessage.objects.create(ticket=ticket, user=request.user, body=body)
    ticket.status = 'open'
    ticket.save(update_fields=['status','updated_at'])
    return redirect('tickets')

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .models import Ticket, TicketMessage

@login_required
def tickets(request):
    if request.method == 'POST':
        subject = request.POST.get('subject','').strip()[:250]
        body = request.POST.get('body','').strip()[:10000]
        if not subject or not body:
            messages.error(request, 'موضوع و متن درخواست پشتیبانی الزامی است.')
            return redirect('tickets')
        Ticket.objects.create(user=request.user, subject=subject, body=body)
        messages.success(request, 'درخواست پشتیبانی ثبت شد.')
        return redirect('tickets')
    return render(request,'support/tickets.html',{'tickets':Ticket.objects.filter(user=request.user).order_by('-updated_at')})

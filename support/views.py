from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect
from .models import Ticket,TicketMessage
@login_required
def tickets(request):
    if request.method=='POST': Ticket.objects.create(user=request.user,subject=request.POST.get('subject',''),body=request.POST.get('body','')); return redirect('tickets')
    return render(request,'support/tickets.html',{'tickets':Ticket.objects.filter(user=request.user)})

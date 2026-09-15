from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Sum
from shop.models import Order
from accounts.models import User
from analytics.models import Event

@staff_member_required
def dashboard(request):
    paid=Order.objects.filter(status__in=['paid','gift'])
    sales=paid.aggregate(v=Sum('total'))['v'] or 0
    users=User.objects.count()
    return render(request,'analytics/dashboard.html',{'sales':sales,'orders':paid.count(),'users':users,'events':Event.objects.count()})

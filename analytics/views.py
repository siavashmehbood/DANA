from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, Sum
from django.shortcuts import render
from django.utils import timezone
from accounts.models import User
from reader.models import ReadingProgress
from shop.models import CartItem, Order
from analytics.models import Event

@staff_member_required
def dashboard(request):
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    paid = Order.objects.filter(status__in=['paid', 'gift'])
    today_paid = paid.filter(created_at__gte=today)
    sales = paid.aggregate(v=Sum('total'))['v'] or 0
    today_sales = today_paid.aggregate(v=Sum('total'))['v'] or 0
    users = User.objects.count()
    paying_users = paid.values('user_id').distinct().count()
    active_readers = ReadingProgress.objects.filter(updated_at__gte=now - timedelta(days=30)).values('user_id').distinct().count()
    new_users = User.objects.filter(date_joined__gte=now - timedelta(days=30)).count()
    aov = paid.aggregate(v=Avg('total'))['v'] or 0
    arpu = (sales / users) if users else 0
    ltv = (sales / paying_users) if paying_users else 0
    conversion = (paying_users * 100 / users) if users else 0
    cart_users = CartItem.objects.values('user_id').distinct().count()
    searches = Event.objects.filter(name='search',created_at__gte=now-timedelta(days=30)).count()
    zero_searches = Event.objects.filter(name='search_zero_result',created_at__gte=now-timedelta(days=30)).count()
    search_success_rate = min(round((max(searches-zero_searches,0)*100/searches),2),100) if searches else 0
    top_zero_searches = list(Event.objects.filter(name='search_zero_result',created_at__gte=now-timedelta(days=30)).values('metadata__query').annotate(count=Count('id')).order_by('-count')[:10])
    relaxed_searches = Event.objects.filter(name='search',created_at__gte=now-timedelta(days=30),metadata__relaxed=True).count()
    zero_rate = round((zero_searches*100/searches),2) if searches else 0
    return render(request, 'analytics/dashboard.html', {'sales': sales, 'today_sales': today_sales, 'orders': paid.count(), 'users': users,
        'events': Event.objects.count(), 'paying_users': paying_users, 'active_readers': active_readers, 'new_users': new_users,
        'aov': round(aov, 0), 'arpu': round(arpu, 0), 'ltv': round(ltv, 0), 'conversion': round(conversion, 2), 'cart_users': cart_users, 'searches': searches, 'zero_searches': zero_searches, 'search_success_rate': search_success_rate, 'relaxed_searches': relaxed_searches, 'zero_rate': zero_rate, 'top_zero_searches': top_zero_searches})

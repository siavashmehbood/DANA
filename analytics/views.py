from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, Sum, Q
from django.shortcuts import render
from django.utils import timezone
from accounts.models import User
from reader.models import AudioProgress, ListeningActivity, ReadingActivity, ReadingProgress
from shop.models import CartItem, Order
from analytics.models import Event

@staff_member_required
def dashboard(request):
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    paid = Order.objects.filter(status__in=['paid', 'gift'])
    order_stats=paid.aggregate(sales=Sum('total'),today_sales=Sum('total',filter=Q(created_at__gte=today)),orders=Count('id'),aov=Avg('total'))
    sales = order_stats['sales'] or 0
    today_sales = order_stats['today_sales'] or 0
    users = User.objects.count()
    paying_users = paid.values('user_id').distinct().count()
    cutoff = now - timedelta(days=30)
    active_reader_ids = set(ReadingActivity.objects.filter(created_at__gte=cutoff).values_list('user_id', flat=True))
    active_reader_ids.update(ListeningActivity.objects.filter(created_at__gte=cutoff).values_list('user_id', flat=True))
    active_readers = len(active_reader_ids)
    new_users = User.objects.filter(date_joined__gte=now - timedelta(days=30)).count()
    aov = order_stats['aov'] or 0
    arpu = (sales / users) if users else 0
    ltv = (sales / paying_users) if paying_users else 0
    conversion = (paying_users * 100 / users) if users else 0
    cart_users = CartItem.objects.values('user_id').distinct().count()
    searches = Event.objects.filter(name='search',created_at__gte=now-timedelta(days=30)).count()
    zero_searches = Event.objects.filter(name='search_zero_result',created_at__gte=now-timedelta(days=30)).count()
    search_success_rate = min(round((max(searches-zero_searches,0)*100/searches),2),100) if searches else 0
    top_zero_searches = list(Event.objects.filter(name='search_zero_result',created_at__gte=now-timedelta(days=30)).values('metadata__query').annotate(count=Count('id')).order_by('-count')[:10])
    relaxed_searches = Event.objects.filter(name='search',created_at__gte=cutoff,metadata__relaxed=True).count()
    relaxed_rate = round((relaxed_searches*100/searches),2) if searches else 0
    zero_rate = min(round((zero_searches*100/searches),2),100) if searches else 0
    return render(request, 'analytics/dashboard.html', {'sales': sales, 'today_sales': today_sales, 'orders': order_stats['orders'], 'users': users,
        'events': Event.objects.count(), 'paying_users': paying_users, 'active_readers': active_readers, 'new_users': new_users,
        'aov': round(aov, 0), 'arpu': round(arpu, 0), 'ltv': round(ltv, 0), 'conversion': round(conversion, 2), 'cart_users': cart_users, 'searches': searches, 'zero_searches': zero_searches, 'search_success_rate': search_success_rate, 'relaxed_searches': relaxed_searches, 'relaxed_rate': relaxed_rate, 'zero_rate': zero_rate, 'top_zero_searches': top_zero_searches})

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum, Q, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from .models import GamificationLevel

PERIODS=[('week','این هفته'),('month','این ماه'),('year','امسال')]
METRICS=[('level','لول'),('study_hours','ساعت مطالعه'),('admin_score','امتیاز مدیر')]

def level_for(user):
    row=GamificationLevel.objects.filter(active=True,min_xp__lte=user.xp).order_by('-min_xp').first()
    return row.order if row else max(1,getattr(user,'level',1))

def period_start(period):
    now=timezone.now()
    if period=='week': return now-timedelta(days=7)
    if period=='month': return now-timedelta(days=30)
    return now-timedelta(days=365)

def metric_value(user,metric,start):
    if metric=='level': return level_for(user)
    if metric=='study_hours':
        from reader.models import ReadingActivity, ListeningActivity
        reading=ReadingActivity.objects.filter(user=user,created_at__gte=start).aggregate(v=Sum('seconds'))['v'] or 0
        listening=ListeningActivity.objects.filter(user=user,created_at__gte=start).aggregate(v=Sum('seconds'))['v'] or 0
        return round((reading+listening)/3600,1)
    try:
        from reader.models import Review
        return Review.objects.filter(user=user,created_at__gte=start,admin_score__isnull=False).aggregate(v=Sum('admin_score'))['v'] or 0
    except Exception: return 0

@login_required
def leaderboard(request):
    period=request.GET.get('period','week')
    metric=request.GET.get('metric','level')
    if period not in dict(PERIODS): period='week'
    if metric not in dict(METRICS): metric='level'
    start=period_start(period)
    people=User.objects.filter(is_active=True,leaderboard_public=True)
    if metric=='study_hours':
        people=people.annotate(reading_seconds=Coalesce(Sum('readingactivity__seconds',filter=Q(readingactivity__created_at__gte=start)),0),listening_seconds=Coalesce(Sum('listeningactivity__seconds',filter=Q(listeningactivity__created_at__gte=start)),0))
        rows=[{'user':u,'level':level_for(u),'value':round((u.reading_seconds+u.listening_seconds)/3600,1)} for u in people]
    elif metric=='admin_score':
        people=people.annotate(score_total=Coalesce(Sum('review__admin_score',filter=Q(review__created_at__gte=start,review__admin_score__isnull=False)),0))
        rows=[{'user':u,'level':level_for(u),'value':u.score_total} for u in people]
    else:
        rows=[{'user':u,'level':level_for(u),'value':level_for(u)} for u in people]
    rows.sort(key=lambda x:(x['value'],x['user'].xp),reverse=True)
    visible=rows[:10]
    mine=next((x for x in rows if x['user'].pk==request.user.pk),None)
    rank=rows.index(mine)+1 if mine else 0
    return render(request,'gamification/leaderboard.html',{'users':visible,'rank':rank,'my_value':mine['value'] if mine else 0,'period':period,'metric':metric,'periods':PERIODS,'metrics':METRICS})

import re
import secrets
from datetime import timedelta
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.conf import settings
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.cache import never_cache
from django.utils.http import url_has_allowed_host_and_scheme
from articles.models import Article
from books.models import Book
from shop.models import CartItem, Entitlement, Referral, Subscription
from reader.models import ReadingProgress, AudioProgress, ReadingGoal
from .models import User, OTPCode, Device, UserSession

def _phone(value):
    value=re.sub(r'[^0-9+]','',value or '')
    if value.startswith('09'): value='+98'+value[1:]
    return value if re.fullmatch(r'\+98(9\d{9})',value) else None

def _session_record(request,user):
    key=request.session.session_key
    if not key: request.session.save(); key=request.session.session_key
    ua=request.headers.get('User-Agent','')[:120]
    device,_=Device.objects.get_or_create(user=user,name=ua); device.last_seen=timezone.now(); device.save(update_fields=['last_seen'])
    UserSession.objects.update_or_create(session_key=key,defaults={'user':user,'device':device,'ip':request.META.get('REMOTE_ADDR'),'user_agent':request.headers.get('User-Agent','')})

def _rate_limited(key,limit,timeout):
    count=cache.get(key,0)
    if count>=limit:return True
    cache.set(key,count+1,timeout=timeout); return False

def _safe_next(request, value):
    return value if value and url_has_allowed_host_and_scheme(value,allowed_hosts={request.get_host()},require_https=request.is_secure()) else '/'

def login_view(request):
    if request.GET.get('ref') and not request.user.is_authenticated:
        code=request.GET.get('ref','').strip().upper()
        if User.objects.filter(referral_code=code).exists(): request.session['referral_code']=code
    if request.method=='POST':
        method=request.POST.get('login_method','otp'); ip=request.META.get('REMOTE_ADDR','unknown')
        if method=='password':
            if _rate_limited(f'dana-login:{ip}',10,300): messages.error(request,'تعداد تلاش‌ها زیاد است؛ چند دقیقه بعد دوباره امتحان کنید.'); return redirect('login')
            username=request.POST.get('username','').strip(); password=request.POST.get('password',''); user=auth.authenticate(request,username=username,password=password)
            if user is not None and user.is_active: auth.login(request,user); _session_record(request,user); return redirect(_safe_next(request,request.POST.get('next')))
            messages.error(request,'نام کاربری یا رمز عبور نادرست است.'); return render(request,'auth/login.html',{'next_url':_safe_next(request,request.POST.get('next'))})
        phone=_phone(request.POST.get('phone'))
        if not phone: messages.error(request,'شماره موبایل معتبر نیست.'); return redirect('login')
        if not request.POST.get('terms'): messages.error(request,'پذیرش قوانین الزامی است.'); return redirect('login')
        if _rate_limited(f'dana-otp:{phone}:{ip}',5,3600): messages.error(request,'تعداد درخواست کد زیاد است؛ بعداً دوباره تلاش کنید.'); return redirect('login')
        if OTPCode.objects.filter(phone=phone,purpose='login',created_at__gt=timezone.now()-timedelta(seconds=30)).exists(): messages.error(request,'لطفاً کمی صبر کنید.'); return redirect('login')
        code=f'{secrets.randbelow(100000):05d}'; OTPCode.objects.create(phone=phone,code=make_password(code),purpose='login',expires_at=timezone.now()+timedelta(minutes=2)); request.session['otp_phone']=phone; request.session['login_next']=_safe_next(request,request.POST.get('next'))
        if settings.DEBUG: print(f'[DANA OTP] {phone}: {code}')
        return redirect('otp')
    return render(request,'auth/login.html',{'next_url':_safe_next(request,request.GET.get('next'))})

def otp(request):
    phone=request.session.get('otp_phone')
    if not phone:return redirect('login')
    if request.method=='POST':
        ip=request.META.get('REMOTE_ADDR','unknown')
        if _rate_limited(f'dana-otp-verify:{phone}:{ip}',10,300):
            messages.error(request,'تعداد تلاش‌ها زیاد است؛ چند دقیقه بعد دوباره امتحان کنید.')
            return redirect('otp')
        row=OTPCode.objects.filter(phone=phone,purpose='login',used=False,expires_at__gt=timezone.now()).order_by('-id').first()
        if row and row.attempts<5 and check_password(request.POST.get('code','').strip(),row.code):
            row.used=True; row.save(update_fields=['used']); user,created=User.objects.get_or_create(phone=phone,defaults={'terms_accepted_at':timezone.now()})
            if not user.is_active: messages.error(request,'این حساب غیرفعال است.'); return redirect('login')
            if not user.terms_accepted_at:user.terms_accepted_at=timezone.now(); user.save(update_fields=['terms_accepted_at'])
            if created:
                referral_code=request.session.pop('referral_code',''); inviter=User.objects.filter(referral_code=referral_code).exclude(pk=user.pk).first()
                if inviter: Referral.objects.get_or_create(inviter=inviter,invitee=user)
            auth.login(request,user); _session_record(request,user); request.session.pop('otp_phone',None); return redirect(request.session.pop('login_next','/'))
        if row: row.attempts+=1; row.save(update_fields=['attempts'])
        messages.error(request,'کد واردشده صحیح نیست یا منقضی شده است.')
    return render(request,'auth/otp.html',{'phone':phone})

@login_required
@never_cache
def dashboard(request):
    user=request.user
    owned=Entitlement.objects.filter(user=user).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).select_related('book__author').order_by('-granted_at')
    valid_book_ids=list(owned.values_list('book_id',flat=True))
    owned_count=len(set(valid_book_ids))
    subscription=Subscription.objects.filter(user=user,status='active',starts_at__lte=timezone.now(),expires_at__gt=timezone.now(),plan__active=True,plan__grants_catalog_access=True).select_related('plan').first()
    if subscription:
        valid_book_ids += list(Book.objects.filter(Q(status='published')|Q(status='scheduled',publish_at__lte=timezone.now()),subscription_included=True).values_list('id',flat=True))
    valid_book_ids=list(set(valid_book_ids))
    progress=ReadingProgress.objects.filter(user=user,book_id__in=valid_book_ids).filter(Q(book__status='published')|Q(book__status='scheduled',book__publish_at__lte=timezone.now())).select_related('book__author').order_by('-updated_at')
    return render(request,'dashboard.html',{'books_count':len(valid_book_ids) if subscription else owned_count,'article_count':Article.objects.filter(published=True).count(),'vocabulary_count':user.saved_words.count(),'cart_count':CartItem.objects.filter(user=user).count(),'latest_articles':Article.objects.filter(published=True).order_by('-created_at')[:5],'owned_books':owned[:8],'reading_progress':progress[:4]})

@login_required
@never_cache
def profile(request):
    if request.method=='POST' and request.POST.get('form')=='goal':
        try:
            weekly_minutes=int(request.POST.get('weekly_minutes',120)); weekly_books=int(request.POST.get('weekly_books',1))
        except (TypeError,ValueError):
            messages.error(request,'هدف مطالعه معتبر نیست.'); return redirect('profile')
        if not 1 <= weekly_minutes <= 10080 or not 1 <= weekly_books <= 100:
            messages.error(request,'هدف مطالعه خارج از محدوده مجاز است.'); return redirect('profile')
        ReadingGoal.objects.update_or_create(user=request.user,defaults={'weekly_minutes':weekly_minutes,'weekly_books':weekly_books})
        messages.success(request,'هدف مطالعه ذخیره شد.'); return redirect('profile')
    if request.method=='POST':
        request.user.first_name=request.POST.get('first_name','').strip(); request.user.last_name=request.POST.get('last_name','').strip(); request.user.email=request.POST.get('email','').strip(); avatar=request.FILES.get('avatar')
        if avatar:
            ext=(avatar.name.rsplit('.',1)[-1].lower() if '.' in avatar.name else '')
            if ext not in {'jpg','jpeg','png','webp'} or not (avatar.content_type or '').startswith('image/') or avatar.size>5*1024*1024: messages.error(request,'تصویر نامعتبر است.'); return redirect('profile')
            request.user.avatar=avatar
        new_password=request.POST.get('new_password','')
        if new_password:
            if not request.user.check_password(request.POST.get('current_password','')):
                messages.error(request,'برای تغییر رمز، رمز فعلی را وارد کنید.'); return redirect('profile')
            if len(new_password)<8: messages.error(request,'رمز عبور باید حداقل ۸ کاراکتر باشد.'); return redirect('profile')
            request.user.set_password(new_password); update_session_auth_hash(request,request.user)
        request.user.save(); messages.success(request,'پروفایل به‌روز شد.')
    sessions=UserSession.objects.filter(user=request.user).select_related('device').order_by('-last_seen')
    goal,_=ReadingGoal.objects.get_or_create(user=request.user)
    week_start=timezone.now()-timedelta(days=7)
    weekly_seconds=sum(ReadingProgress.objects.filter(user=request.user,updated_at__gte=week_start).values_list('seconds',flat=True))
    weekly_audio_seconds=sum(ReadingProgress.objects.filter(user=request.user,updated_at__gte=week_start).values_list('audio_seconds',flat=True))
    completed_books=ReadingProgress.objects.filter(user=request.user,progress__gte=100).count()
    total_reading_seconds=sum(ReadingProgress.objects.filter(user=request.user).values_list('seconds',flat=True))
    total_audio_seconds=sum(ReadingProgress.objects.filter(user=request.user).values_list('audio_seconds',flat=True))
    return render(request,'profile.html',{'login_sessions':sessions,'reading_goal':goal,'weekly_minutes_done':(weekly_seconds+weekly_audio_seconds)//60,'completed_books':completed_books,'total_reading_minutes':total_reading_seconds//60,'total_audio_minutes':total_audio_seconds//60})

@login_required
def logout_others(request):
    if request.method=='POST':
        other_keys=list(UserSession.objects.filter(user=request.user).exclude(session_key=request.session.session_key).values_list('session_key',flat=True))
        Session.objects.filter(session_key__in=other_keys).delete()
        UserSession.objects.filter(session_key__in=other_keys).delete()
        messages.success(request,'جلسات دیگر بسته شدند.')
    return redirect('profile')

@login_required
def deactivate(request):
    if request.method=='POST': request.user.is_active=False; request.user.is_deactivated=True; request.user.save(update_fields=['is_active','is_deactivated']); auth.logout(request); return redirect('/')
    return render(request,'auth/deactivate.html')

def logout_view(request):
    if request.user.is_authenticated: UserSession.objects.filter(session_key=request.session.session_key).delete()
    auth.logout(request); return redirect('/')


@login_required
@never_cache
def library(request):
    user=request.user
    owned=list(Entitlement.objects.filter(user=user).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).filter(Q(book__status='published')|Q(book__status='scheduled',book__publish_at__lte=timezone.now())).select_related('book__author','book__category').prefetch_related('book__chapters').order_by('-granted_at'))
    active_subscription=Subscription.objects.filter(user=user,status='active',starts_at__lte=timezone.now(),expires_at__gt=timezone.now(),plan__active=True,plan__grants_catalog_access=True).select_related('plan').first()
    entitled_ids={item.book_id for item in owned}
    books=[item.book for item in owned]
    if active_subscription:
        subscription_books=Book.objects.filter(Q(status='published')|Q(status='scheduled',publish_at__lte=timezone.now()),subscription_included=True).exclude(pk__in=entitled_ids).select_related('author','category').prefetch_related('chapters').order_by('-created_at')[:500]
        books.extend(subscription_books)
    book_ids=[book.id for book in books]
    pmap={p.book_id:p for p in ReadingProgress.objects.filter(user=user,book_id__in=book_ids)}
    amap={}
    for item in AudioProgress.objects.filter(user=user,book_id__in=book_ids).order_by('book_id','-updated_at'):
        amap.setdefault(item.book_id,item)
    rows=[]
    for book in books:
        has_audio=bool(book.audio) or any(ch.audio for ch in book.chapters.all())
        rows.append({'book':book,'progress':pmap.get(book.id),'audio_progress':amap.get(book.id),'has_audio':has_audio,'source':'purchased' if book.id in entitled_ids else 'subscription'})
    state=request.GET.get('state','all')
    kind=request.GET.get('kind','all')
    source=request.GET.get('source','all')
    sort=request.GET.get('sort','recent')
    if state not in {'all','reading','completed','unread'}: state='all'
    if kind not in {'all','audio','text'}: kind='all'
    if source not in {'all','purchased','subscription'}: source='all'
    if sort not in {'recent','title','progress'}: sort='recent'
    if state=='reading': rows=[row for row in rows if row['progress'] and 0 < row['progress'].progress < 100]
    elif state=='completed': rows=[row for row in rows if row['progress'] and row['progress'].progress >= 100]
    elif state=='unread': rows=[row for row in rows if not row['progress'] or row['progress'].progress <= 0]
    if kind=='audio': rows=[row for row in rows if row['book'].audio or any(ch.audio for ch in row['book'].chapters.all())]
    elif kind=='text': rows=[row for row in rows if row['book'].pdf or any(ch.text for ch in row['book'].chapters.all())]
    if source!='all': rows=[row for row in rows if row['source']==source]
    if sort=='title': rows.sort(key=lambda row: row['book'].name)
    elif sort=='progress': rows.sort(key=lambda row: float(row['progress'].progress) if row['progress'] else -1,reverse=True)
    visible_count=len(rows)
    return render(request,'library.html',{'library_rows':rows,'state':state,'kind':kind,'source':source,'sort':sort,'library_count':len(books),'visible_count':visible_count,'active_subscription':active_subscription})

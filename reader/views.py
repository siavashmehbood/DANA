from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.db.models import Q
from django.db import models, transaction
from books.models import Book
from shop.models import Entitlement, Subscription
from .models import ReadingProgress, Bookmark, Highlight, Note, SavedWord, Review, ProblemReport
from gamification.services import record_study_activity


def _has_access(user, book):
    if book.visibility == 'public' and book.price == 0:
        return True
    if not user.is_authenticated:
        return False
    if Entitlement.objects.filter(user=user, book=book).filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())).exists():
        return True
    if not book.subscription_included:
        return False
    now=timezone.now()
    return Subscription.objects.filter(user=user,status='active',starts_at__lte=now,expires_at__gt=now,plan__active=True,plan__grants_catalog_access=True).exists()


@login_required
@never_cache
def reader(request, pk):
    book = get_object_or_404(Book.objects.prefetch_related('chapters'), pk=pk)
    if not book.is_published:
        response=HttpResponseForbidden('کتاب هنوز منتشر نشده است.')
        response['Cache-Control']='private, no-store'
        return response
    accessible = _has_access(request.user, book)
    if not accessible:
        response=HttpResponseForbidden('برای مطالعه این کتاب دسترسی فعال لازم است.')
        response['Cache-Control']='private, no-store'
        return response
    owned = Entitlement.objects.filter(user=request.user,book=book).filter(models.Q(expires_at__isnull=True)|models.Q(expires_at__gt=timezone.now())).exists()
    saved = ReadingProgress.objects.filter(user=request.user, book=book).select_related('current_chapter').first()
    bookmark_query=request.GET.get('bookmark_q','').strip()[:150]
    note_query=request.GET.get('note_q','').strip()[:200]
    highlight_query=request.GET.get('highlight_q','').strip()[:200]
    bookmarks = Bookmark.objects.filter(user=request.user, book=book)
    notes = Note.objects.filter(user=request.user, book=book)
    highlights = Highlight.objects.filter(user=request.user, book=book)
    if highlight_query: highlights=highlights.filter(text__icontains=highlight_query)
    highlights=highlights.order_by('-created_at')[:500]
    if bookmark_query: bookmarks=bookmarks.filter(title__icontains=bookmark_query)
    if note_query: notes=notes.filter(text__icontains=note_query)
    bookmarks=bookmarks.order_by('page')[:500]
    notes=notes.order_by('-created_at')[:500]
    response=render(request, 'reader/reader.html', {'book': book, 'owned': owned, 'accessible': accessible, 'saved': saved, 'bookmarks': bookmarks, 'notes': notes, 'bookmark_query':bookmark_query, 'note_query':note_query, 'highlights':highlights, 'highlight_query':highlight_query})
    response['Cache-Control']='private, no-store'
    response['X-Robots-Tag']='noindex, nofollow'
    response['Referrer-Policy']='same-origin'
    return response


@login_required
@require_POST
def progress(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if not book.is_published or not _has_access(request.user, book): return HttpResponseForbidden('Access denied')
    try:
        value=max(0,min(100,float(request.POST.get('progress',0)))); page=min(1000000,max(0,int(request.POST.get('page',0))))
        seconds=min(31536000,max(0,int(request.POST.get('seconds',0)))); audio_seconds=min(31536000,max(0,int(request.POST.get('audio_seconds',0))))
        chapter_id=request.POST.get('chapter_id') or None
    except (TypeError,ValueError): return JsonResponse({'error':'Invalid progress data'},status=400)
    chapter = None
    if chapter_id:
        try:
            chapter = book.chapters.get(pk=chapter_id)
        except (ValueError, TypeError, book.chapters.model.DoesNotExist):
            return JsonResponse({'error':'Invalid chapter'},status=400)
    with transaction.atomic():
        saved=ReadingProgress.objects.select_for_update().filter(user=request.user,book=book).first()
        if saved is None:
            saved=ReadingProgress.objects.create(user=request.user,book=book)
        added_study_time = seconds > saved.seconds or audio_seconds > saved.audio_seconds
        saved.progress=max(float(saved.progress),value); saved.current_page=max(saved.current_page,page)
        saved.seconds=max(saved.seconds,seconds); saved.audio_seconds=max(saved.audio_seconds,audio_seconds)
        if chapter is not None and (saved.current_chapter_id is None or chapter.order >= saved.current_chapter.order):
            saved.current_chapter = chapter
        fields=['progress','current_page','seconds','audio_seconds','updated_at']
        if chapter is not None and saved.current_chapter_id == chapter.id:
            fields.append('current_chapter')
        saved.save(update_fields=fields)
    if added_study_time:
        record_study_activity(request.user)
    response=JsonResponse({'ok':True,'progress':float(saved.progress),'page':saved.current_page,'audio_seconds':saved.audio_seconds})
    response['Cache-Control']='no-store'
    return response


@login_required
@require_POST
def bookmark(request, pk):
    book=get_object_or_404(Book,pk=pk)
    if not book.is_published or not _has_access(request.user,book): return HttpResponseForbidden('Access denied')
    try: page=min(1000000,max(0,int(request.POST.get('page',0))))
    except (TypeError,ValueError): return JsonResponse({'error':'Invalid page'},status=400)
    title=request.POST.get('title','').strip()[:150]
    item,created=Bookmark.objects.get_or_create(user=request.user,book=book,page=page,defaults={'title':title})
    if not created and title and item.title != title:
        item.title=title; item.save(update_fields=['title'])
    return JsonResponse({'ok':True,'created':created,'id':item.id,'page':item.page,'title':item.title})


@login_required
@require_POST
def highlight(request, pk):
    book=get_object_or_404(Book,pk=pk)
    if not book.is_published or not _has_access(request.user,book): return HttpResponseForbidden('Access denied')
    try: page=min(1000000,max(0,int(request.POST.get('page',0))))
    except (TypeError,ValueError): return JsonResponse({'error':'Invalid page'},status=400)
    text=request.POST.get('text','').strip()[:5000]
    color=request.POST.get('color','yellow')
    if color not in {'yellow','green','blue','pink'}: color='yellow'
    if not text: return JsonResponse({'error':'Highlight is empty'},status=400)
    item,created=Highlight.objects.get_or_create(user=request.user,book=book,page=page,text=text,defaults={'color':color})
    return JsonResponse({'ok':True,'created':created,'id':item.id,'page':item.page,'text':item.text})


@login_required
@require_POST
def delete_highlight(request, pk, highlight_id):
    book=get_object_or_404(Book,pk=pk)
    if not book.is_published or not _has_access(request.user,book): return HttpResponseForbidden('Access denied')
    item=get_object_or_404(Highlight,pk=highlight_id,user=request.user,book=book)
    item.delete()
    return JsonResponse({'ok':True})


@login_required
@require_POST
def note(request, pk):
    book=get_object_or_404(Book,pk=pk)
    if not book.is_published or not _has_access(request.user,book): return HttpResponseForbidden('Access denied')
    try: page=min(1000000,max(0,int(request.POST.get('page',0))))
    except (TypeError,ValueError): return JsonResponse({'error':'Invalid page'},status=400)
    text=request.POST.get('text','').strip()[:5000]
    if not text: return JsonResponse({'error':'Note is empty'},status=400)
    item,created=Note.objects.get_or_create(user=request.user,book=book,page=page,text=text)
    return JsonResponse({'ok':True,'created':created,'id':item.id,'page':item.page,'text':item.text})


@login_required
@require_POST
def delete_bookmark(request, pk, bookmark_id):
    book=get_object_or_404(Book,pk=pk)
    if not book.is_published or not _has_access(request.user,book): return HttpResponseForbidden('Access denied')
    item=get_object_or_404(Bookmark,pk=bookmark_id,user=request.user,book=book)
    item.delete()
    return JsonResponse({'ok':True})


@login_required
@require_POST
def delete_note(request, pk, note_id):
    book=get_object_or_404(Book,pk=pk)
    if not book.is_published or not _has_access(request.user,book): return HttpResponseForbidden('Access denied')
    item=get_object_or_404(Note,pk=note_id,user=request.user,book=book)
    item.delete()
    return JsonResponse({'ok':True})


@login_required
@require_POST
def save_word(request, slug):
    from articles.models import Article
    import re
    article=get_object_or_404(Article,slug=slug,published=True)
    word=re.sub(r'\s+',' ',request.POST.get('word','').strip())
    if not word: return JsonResponse({'ok':False,'error':'کلمه یا عبارت خالی است.'},status=400)
    if len(word)>180: return JsonResponse({'ok':False,'error':'کلمه یا عبارت بیش از حد طولانی است.'},status=400)
    normalized=' '.join(word.replace('ي','ی').replace('ك','ک').replace('\u200c',' ').casefold().split())
    item,created=SavedWord.objects.get_or_create(user=request.user,normalized_word=normalized,defaults={'word':word,'article':article})
    if not created and not item.article_id: item.article=article; item.save(update_fields=['article'])
    return JsonResponse({'ok':True,'created':created,'id':item.id,'word':item.word})


@login_required
@never_cache
def vocabulary(request):
    query=request.GET.get('q','').strip()[:180]
    query=' '.join(query.replace('ي','ی').replace('ك','ک').replace('\u200c',' ').split())
    words=SavedWord.objects.filter(user=request.user).select_related('article')
    words=words.filter(Q(article__isnull=True)|Q(article__published=True))
    if query:
        variants={query,query.replace('ی','ي').replace('ک','ك')}
        q=Q()
        for term in variants: q |= Q(word__icontains=term)
        words=words.filter(q)
    response=render(request,'reader/vocabulary.html',{'words':words[:500],'query':query})
    response['Cache-Control']='private, no-store'
    response['X-Robots-Tag']='noindex, nofollow'
    response['Referrer-Policy']='same-origin'
    return response


@login_required
@require_POST
def delete_word(request, pk):
    item=get_object_or_404(SavedWord,pk=pk,user=request.user); item.delete(); return redirect('reader_vocabulary')


@login_required
@require_POST
def review(request, pk):
    book=get_object_or_404(Book,pk=pk)
    if not book.is_published or not _has_access(request.user,book):
        return HttpResponseForbidden('برای ثبت نظر باید به کتاب دسترسی داشته باشید.')
    try: rating=int(request.POST.get('rating',0))
    except (TypeError,ValueError): rating=0
    text=request.POST.get('text','').strip()[:4000]
    if rating not in range(1,6) or not text:
        return JsonResponse({'error':'امتیاز و متن نظر معتبر نیست.'},status=400)
    Review.objects.update_or_create(user=request.user,book=book,defaults={'rating':rating,'text':text,'approved':False,'admin_score':None,'admin_reply':''})
    return JsonResponse({'ok':True,'message':'نظر شما برای بررسی ثبت شد.'})


@login_required
@require_POST
def report_problem(request, pk):
    book=get_object_or_404(Book,pk=pk)
    if not book.is_published or not _has_access(request.user,book):
        return HttpResponseForbidden('برای گزارش مشکل باید به کتاب دسترسی داشته باشید.')
    text=request.POST.get('text','').strip()[:4000]
    recent=ProblemReport.objects.filter(user=request.user,created_at__gte=timezone.now()-timezone.timedelta(hours=1)).count()
    if recent >= 10:
        return JsonResponse({'error':'تعداد گزارش‌ها زیاد است؛ کمی بعد دوباره تلاش کنید.'},status=429)
    if not text:
        return JsonResponse({'error':'شرح مشکل خالی است.'},status=400)
    ProblemReport.objects.create(user=request.user,book=book,text=text)
    return JsonResponse({'ok':True,'message':'گزارش برای بررسی ثبت شد.'})

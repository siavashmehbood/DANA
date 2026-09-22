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
from .models import ReadingProgress, ReadingActivity, ListeningActivity, AudioProgress, Bookmark, Highlight, Note, SavedWord, Review, ProblemReport
from gamification.services import record_study_activity


def _has_access(user, book):
    if book.visibility == 'password':
        return False
    if book.visibility == 'public' and book.price == 0:
        return True
    if not user.is_authenticated:
        return False
    if Entitlement.objects.filter(user=user, book=book).filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())).exists():
        return True
    if not book.subscription_included:
        return False
    now=timezone.now()
    return Subscription.objects.filter(user=user,status='active',starts_at__lte=now,expires_at__gt=now,plan__grants_catalog_access=True).exists()


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
        # Reader links can outlive a subscription. Return the user to the product
        # page where purchase/subscription recovery options are available instead
        # of leaving them at a dead-end 403.
        response=redirect('book_detail',slug=book.slug)
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
    has_audio=bool(book.audio) or book.chapters.exclude(audio='').exists()
    text_chapters=list(book.chapters.exclude(text='').order_by('order'))
    response=render(request, 'reader/reader.html', {'book': book, 'has_audio':has_audio, 'text_chapters':text_chapters, 'owned': owned, 'accessible': accessible, 'saved': saved, 'bookmarks': bookmarks, 'notes': notes, 'bookmark_query':bookmark_query, 'note_query':note_query, 'highlights':highlights, 'highlight_query':highlight_query})
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
        reading_delta=max(0,seconds-saved.seconds)
        added_study_time = reading_delta > 0 or audio_seconds > saved.audio_seconds
        saved.progress=max(float(saved.progress),value)
        saved.seconds=max(saved.seconds,seconds); saved.audio_seconds=max(saved.audio_seconds,audio_seconds)
        # Page/chapter are resume cursors, not achievements. Persist the reader's
        # latest valid location so intentionally revisiting an earlier chapter is
        # respected after refresh/login while overall completion stays monotonic.
        if chapter is not None:
            saved.current_chapter = chapter
            saved.current_page = page
        else:
            saved.current_page=max(saved.current_page,page)
        fields=['progress','current_page','seconds','audio_seconds','updated_at']
        if chapter is not None and saved.current_chapter_id == chapter.id:
            fields.append('current_chapter')
        saved.save(update_fields=fields)
        if reading_delta:
            ReadingActivity.objects.create(user=request.user,book=book,seconds=reading_delta)
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
    if not (article.full_text or article.full_text_fa or article.abstract or article.abstract_fa):
        return JsonResponse({'ok':False,'error':'محتوای قابل مطالعه برای این مقاله موجود نیست.'},status=400)
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
    from django.core.paginator import Paginator
    page_obj=Paginator(words,50).get_page(request.GET.get('page',1))
    word_count=words.count()
    response=render(request,'reader/vocabulary.html',{'words':page_obj.object_list,'page_obj':page_obj,'query':query,'word_count':word_count})
    response['Cache-Control']='private, no-store'
    response['X-Robots-Tag']='noindex, nofollow'
    response['Referrer-Policy']='same-origin'
    return response


@login_required
@require_POST
def delete_word(request, pk):
    item=get_object_or_404(SavedWord,pk=pk,user=request.user)
    item.delete()
    return redirect('reader_vocabulary')


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


@login_required
@never_cache
def audio_player(request, pk):
    book=get_object_or_404(Book.objects.prefetch_related('chapters'),pk=pk)
    if not book.is_published or not _has_access(request.user,book):
        return HttpResponseForbidden('برای شنیدن این کتاب دسترسی فعال لازم است.')
    chapters=list(book.chapters.exclude(audio='').order_by('order'))
    has_book_audio=bool(book.audio)
    if not chapters and not has_book_audio:
        raise Http404
    progress={p.chapter_id:p for p in AudioProgress.objects.filter(user=request.user,book=book)}
    latest=AudioProgress.objects.filter(user=request.user,book=book).order_by('-updated_at').first()
    has_text=bool(book.pdf) or any(bool(ch.text and ch.text.strip()) for ch in book.chapters.all())
    response=render(request,'reader/audio_player.html',{'book':book,'chapters':chapters,'audio_progress':progress,'latest_audio':latest,'latest_chapter_id':latest.chapter_id if latest else None,'has_book_audio':has_book_audio,'has_text':has_text})
    response['Cache-Control']='private, no-store'
    response['X-Robots-Tag']='noindex, nofollow'
    response['Referrer-Policy']='same-origin'
    return response


@login_required
@require_POST
def audio_progress(request, pk):
    book=get_object_or_404(Book,pk=pk)
    if not book.is_published or not _has_access(request.user,book):
        return HttpResponseForbidden('Access denied')
    chapter_id=request.POST.get('chapter_id') or None
    try:
        position=max(0,min(31536000,int(float(request.POST.get('position',0)))))
        duration=max(0,min(31536000,int(float(request.POST.get('duration',0)))))
        listened_delta=max(0,min(3600,int(float(request.POST.get('listened_delta',0)))))
    except (TypeError,ValueError):
        return JsonResponse({'error':'Invalid audio progress'},status=400)
    chapter=None
    if chapter_id:
        try: chapter=book.chapters.get(pk=chapter_id)
        except (ValueError,TypeError,book.chapters.model.DoesNotExist):
            return JsonResponse({'error':'Invalid chapter'},status=400)
    if chapter is None and not book.audio:
        return JsonResponse({'error':'Audio unavailable'},status=400)
    completed=bool(duration and position >= max(0,duration-5))
    with transaction.atomic():
        item=AudioProgress.objects.select_for_update().filter(user=request.user,book=book,chapter=chapter).first()
        if item is None:
            item=AudioProgress.objects.create(user=request.user,book=book,chapter=chapter,position_seconds=position,duration_seconds=duration,completed=completed)
        else:
            # Audio position is a resume cursor, not a monotonic achievement.
            # Persist intentional backward seeks so refresh/login resumes where the
            # listener actually stopped; completion itself remains monotonic.
            item.position_seconds=position
            item.duration_seconds=max(item.duration_seconds,duration)
            item.completed=item.completed or completed
            item.save(update_fields=['position_seconds','duration_seconds','completed','updated_at'])
        if listened_delta:
            ListeningActivity.objects.create(user=request.user,book=book,seconds=listened_delta)
    if listened_delta:
        record_study_activity(request.user)
    aggregate=ReadingProgress.objects.filter(user=request.user,book=book).first()
    # AudioProgress positions are resume cursors and may move backwards after a
    # seek. They are not listening-duration telemetry, so do not aggregate them
    # into ReadingProgress.audio_seconds or use them as a study-time signal.
    audio_complete=completed and chapter is None
    if chapter is not None and completed:
        audio_chapter_ids=list(book.chapters.exclude(audio='').values_list('id',flat=True))
        audio_complete=bool(audio_chapter_ids) and not AudioProgress.objects.filter(user=request.user,book=book,chapter_id__in=audio_chapter_ids,completed=False).exists() and AudioProgress.objects.filter(user=request.user,book=book,chapter_id__in=audio_chapter_ids,completed=True).count()==len(audio_chapter_ids)
    if aggregate is None:
        aggregate=ReadingProgress.objects.create(user=request.user,book=book,current_chapter=chapter,progress=100 if audio_complete else 0)
    else:
        if chapter is not None: aggregate.current_chapter=chapter
        if audio_complete: aggregate.progress=100
        aggregate.save(update_fields=['current_chapter','progress','updated_at'])
    return JsonResponse({'ok':True,'position':item.position_seconds,'duration':item.duration_seconds,'completed':item.completed})

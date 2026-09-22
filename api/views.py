import json
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from analytics.models import Event

ALLOWED_EVENT_NAMES = {
    'reader_opened', 'reader_progress', 'audio_started', 'audio_progress',
    'book_viewed', 'article_viewed', 'recommendation_clicked', 'checkout_started',
}


@login_required
@require_POST
@never_cache
def event(request):
    key = f'dana-api-event:{request.user.pk}'
    count = cache.get(key, 0)
    if count >= 60:
        return JsonResponse({'ok': False, 'error': 'rate_limited'}, status=429)
    cache.set(key, count + 1, timeout=60)
    if len(request.body) > 20000:
        return JsonResponse({'ok': False, 'error': 'payload_too_large'}, status=413)
    try:
        data = json.loads(request.body or '{}')
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'invalid_json'}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'ok': False, 'error': 'object_required'}, status=400)
    name = data.get('name')
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
        return JsonResponse({'ok': False, 'error': 'invalid_name'}, status=400)
    name = name.strip()
    if name not in ALLOWED_EVENT_NAMES:
        return JsonResponse({'ok': False, 'error': 'unsupported_event'}, status=400)
    value = data.get('value', 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or abs(value) > 1000000000:
        return JsonResponse({'ok': False, 'error': 'invalid_value'}, status=400)
    metadata = data.get('metadata', {})
    if not isinstance(metadata, dict):
        return JsonResponse({'ok': False, 'error': 'metadata_object_required'}, status=400)
    try:
        metadata_json = json.dumps(metadata, ensure_ascii=False)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'invalid_metadata'}, status=400)
    if len(metadata) > 50:
        return JsonResponse({'ok': False, 'error': 'metadata_too_many_fields'}, status=400)
    if any(len(str(k)) > 100 or len(str(v)) > 2000 for k, v in metadata.items()):
        return JsonResponse({'ok': False, 'error': 'metadata_field_too_large'}, status=400)
    if len(metadata_json) > 10000:
        return JsonResponse({'ok': False, 'error': 'metadata_too_large'}, status=400)
    if not request.session.session_key:
        request.session.save()
    Event.objects.create(user=request.user, name=name, value=value, metadata=metadata, session_key=request.session.session_key or '')
    return JsonResponse({'ok': True})

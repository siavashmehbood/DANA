import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from analytics.models import Event
@require_POST
@login_required
def event(request):
    try:
        data = json.loads(request.body or '{}')
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'invalid_json'}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'ok': False, 'error': 'object_required'}, status=400)
    metadata = data.get('metadata', {})
    if not isinstance(metadata, dict):
        return JsonResponse({'ok': False, 'error': 'metadata_object_required'}, status=400)
    Event.objects.create(
        user=request.user,
        name=str(data.get('name', 'unknown'))[:80],
        metadata=metadata,
    )
    return JsonResponse({'ok': True})

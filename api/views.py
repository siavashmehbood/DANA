import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from analytics.models import Event
@require_POST
@login_required
def event(request):
    data=json.loads(request.body or '{}'); Event.objects.create(user=request.user,name=str(data.get('name','unknown'))[:80],metadata=data.get('metadata',{})); return JsonResponse({'ok':True})

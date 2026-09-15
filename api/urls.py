from django.urls import path
from .views import event
urlpatterns=[path('event/',event,name='api_event')]

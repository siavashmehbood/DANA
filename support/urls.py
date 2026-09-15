from django.urls import path
from .views import tickets
urlpatterns=[path('',tickets,name='tickets')]

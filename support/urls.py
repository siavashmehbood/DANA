from django.urls import path
from .views import tickets, reply_ticket
urlpatterns=[
    path('',tickets,name='tickets'),
    path('<int:pk>/reply/',reply_ticket,name='ticket_reply'),
]

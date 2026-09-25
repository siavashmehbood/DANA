from django.urls import path
from .views import notifications, mark_read, mark_all_read
urlpatterns=[
    path('', notifications, name='notifications'),
    path('<int:pk>/read/', mark_read, name='notification_mark_read'),
    path('read-all/', mark_all_read, name='notifications_mark_all_read'),
]

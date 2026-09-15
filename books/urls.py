from django.urls import path
from .views import listing,detail
urlpatterns=[path('',listing,name='books'),path('<slug:slug>/',detail,name='book_detail')]

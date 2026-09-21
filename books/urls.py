from django.urls import path
from .views import listing,detail,secure_file
urlpatterns=[path('',listing,name='books'),path('<int:pk>/file/<str:kind>/',secure_file,name='book_secure_file'),path('<slug:slug>/',detail,name='book_detail')]

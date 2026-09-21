from django.urls import path
from .views import listing,detail,secure_file
urlpatterns=[
 path('',listing,name='books'),
 path('<int:pk>/file/<str:kind>/',secure_file,name='book_secure_file'),
 path('<int:pk>/chapter/<int:chapter_id>/audio/',secure_file,{'kind':'chapter_audio'},name='chapter_secure_audio'),
 path('<slug:slug>/',detail,name='book_detail'),
]

from django.urls import path
from .views import reader, progress, bookmark, note, save_word, vocabulary, delete_word

urlpatterns = [
    path('vocabulary/', vocabulary, name='reader_vocabulary'),
    path('vocabulary/<int:pk>/delete/', delete_word, name='reader_delete_word'),
    path('article/<slug:slug>/save-word/', save_word, name='reader_save_word'),
    path('<int:pk>/', reader, name='reader'),
    path('<int:pk>/progress/', progress, name='reader_progress'),
    path('<int:pk>/bookmark/', bookmark, name='reader_bookmark'),
    path('<int:pk>/note/', note, name='reader_note'),
]

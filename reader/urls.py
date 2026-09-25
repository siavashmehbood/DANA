from django.urls import path
from .views import reader, progress, bookmark, highlight, delete_highlight, note, delete_bookmark, delete_note, save_word, vocabulary, delete_word, review, report_problem, audio_player, audio_progress

urlpatterns = [
    path('vocabulary/', vocabulary, name='reader_vocabulary'),
    path('vocabulary/<int:pk>/delete/', delete_word, name='reader_delete_word'),
    path('article/<str:slug>/save-word/', save_word, name='reader_save_word'),
    path('<int:pk>/audio/', audio_player, name='audio_player'),
    path('<int:pk>/audio/progress/', audio_progress, name='audio_progress'),
    path('<int:pk>/', reader, name='reader'),
    path('<int:pk>/progress/', progress, name='reader_progress'),
    path('<int:pk>/bookmark/', bookmark, name='reader_bookmark'),
    path('<int:pk>/note/', note, name='reader_note'),
    path('<int:pk>/highlight/', highlight, name='reader_highlight'),
    path('<int:pk>/highlight/<int:highlight_id>/delete/', delete_highlight, name='reader_delete_highlight'),
    path('<int:pk>/bookmark/<int:bookmark_id>/delete/', delete_bookmark, name='reader_delete_bookmark'),
    path('<int:pk>/note/<int:note_id>/delete/', delete_note, name='reader_delete_note'),
    path('<int:pk>/review/', review, name='reader_review'),
    path('<int:pk>/report/', report_problem, name='reader_report_problem'),
]

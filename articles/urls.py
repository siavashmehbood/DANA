from django.urls import path
from .views import article_download, listing, detail, translate_selection, library_action, annotation_create, research_library, annotation_delete, annotation_update, reading_progress, bookmark_toggle, citation_export, pdf_reader

urlpatterns = [
    path('', listing, name='article_list'),
    path('library/', research_library, name='article_library'),
    path('<str:slug>/pdf/', pdf_reader, name='article_pdf_reader'),
    path('<str:slug>/translate/', translate_selection, name='article_translate_selection'),
    path('<str:slug>/library/', library_action, name='article_library_action'),
    path('<str:slug>/annotate/', annotation_create, name='article_annotation_create'),
    path('annotation/<int:pk>/delete/', annotation_delete, name='article_annotation_delete'),
    path('annotation/<int:pk>/update/', annotation_update, name='article_annotation_update'),
    path('<str:slug>/progress/', reading_progress, name='article_reading_progress'),
    path('<str:slug>/bookmark/', bookmark_toggle, name='article_bookmark_toggle'),
    path('<str:slug>/citation/', citation_export, name='article_citation_export'),
    path('<str:slug>/download/', article_download, name='article_download'),
    path('<str:slug>/', detail, name='article_detail'),
]

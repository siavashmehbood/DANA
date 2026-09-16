from django.urls import path
from .views import article_download, listing, detail, translate_selection, library_action, annotation_create, research_library, annotation_delete, reading_progress, citation_export, pdf_reader

urlpatterns = [
    path('', listing, name='article_list'),
    path('library/', research_library, name='article_library'),
    path('<slug:slug>/pdf/', pdf_reader, name='article_pdf_reader'),
    path('<slug:slug>/translate/', translate_selection, name='article_translate_selection'),
    path('<slug:slug>/library/', library_action, name='article_library_action'),
    path('<slug:slug>/annotate/', annotation_create, name='article_annotation_create'),
    path('annotation/<int:pk>/delete/', annotation_delete, name='article_annotation_delete'),
    path('<slug:slug>/progress/', reading_progress, name='article_reading_progress'),
    path('<slug:slug>/citation/', citation_export, name='article_citation_export'),
    path('<slug:slug>/download/', article_download, name='article_download'),
    path('<slug:slug>/', detail, name='article_detail'),
]

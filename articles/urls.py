from django.urls import path
from .views import article_download, listing, detail, translate_selection

urlpatterns = [
    path('', listing, name='article_list'),
    path('<slug:slug>/translate/', translate_selection, name='article_translate_selection'),
    path('<slug:slug>/download/', article_download, name='article_download'),
    path('<slug:slug>/', detail, name='article_detail'),
]

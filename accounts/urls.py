from django.urls import path
from .views import dashboard, library, login_view, register_view, otp, profile, logout_others, deactivate, logout_view

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),
    path('library/', library, name='library'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('otp/', otp, name='otp'),
    path('profile/', profile, name='profile'),
    path('logout/', logout_view, name='logout'),
    path('logout-others/', logout_others, name='logout_others'),
    path('deactivate/', deactivate, name='deactivate'),
]

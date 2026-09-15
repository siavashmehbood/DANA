from django.urls import path
from .views import dashboard, login_view, otp, profile, logout_others, deactivate, logout_view

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),
    path('login/', login_view, name='login'),
    path('otp/', otp, name='otp'),
    path('profile/', profile, name='profile'),
    path('logout/', logout_view, name='logout'),
    path('logout-others/', logout_others, name='logout_others'),
    path('deactivate/', deactivate, name='deactivate'),
]

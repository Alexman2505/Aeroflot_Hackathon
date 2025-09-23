from django.urls import path
from . import views


app_name = 'about'


urlpatterns = [
    path('team/', views.AboutTeamView.as_view(), name='team'),
    path('tech/', views.AboutTechView.as_view(), name='tech'),
]

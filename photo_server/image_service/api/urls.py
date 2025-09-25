from django.urls import path
from . import views

# наш основной url приложения
urlpatterns = [
    path('', views.index, name='index'),
    path('clear-session/', views.clear_session, name='clear_session'),
]

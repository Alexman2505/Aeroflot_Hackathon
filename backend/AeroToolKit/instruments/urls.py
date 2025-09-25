from django.urls import path

from . import views


app_name = 'instruments'


urlpatterns = [
    path('', views.index, name='index'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path(
        'instrument/<int:instrument_id>/',
        views.instrument_detail,
        name='instrument_detail',
    ),
    path('create/', views.instrument_create, name='instrument_create'),
    path(
        'instruments/<int:instrument_id>/edit/',
        views.instrument_edit,
        name='instrument_edit',
    ),
]

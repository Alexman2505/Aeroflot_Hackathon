from django.urls import path
from . import views


app_name = 'instruments'
"""
Пространство имен для URL-адресов приложения instruments.

Позволяет однозначно идентифицировать URL patterns этого приложения
при использовании в шаблонах и коде через 'instruments:name'.
"""

urlpatterns = [
    # Главная страница со списком всех инструментов
    path('', views.index, name='index'),
    # Страница профиля пользователя с его инструментами
    path('profile/<str:username>/', views.profile, name='profile'),
    # Детальная страница конкретного инструмента
    path(
        'instruments/<int:instrument_id>/',
        views.instrument_detail,
        name='instrument_detail',
    ),
    # Страница создания нового инструмента
    path('create/', views.instrument_create, name='instrument_create'),
    # Страница редактирования существующего инструмента
    path(
        'instruments/<int:instrument_id>/edit/',
        views.instrument_edit,
        name='instrument_edit',
    ),
    # Страница удаления существующего инструмента
    path(
        'instruments/<int:instrument_id>/delete/',
        views.instrument_delete,
        name='instrument_delete',
    ),
]

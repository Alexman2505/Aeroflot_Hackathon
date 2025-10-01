from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

# Базовые URL patterns для приложения API
urlpatterns = [
    # Главная страница приложения API
    path('', views.index, name='index'),
    # Endpoint для очистки сессии пользователя
    path('clear-session/', views.clear_session, name='clear_session'),
]

# Добавление статических и медиа файлов в режиме разработки (DEBUG)
if settings.DEBUG:
    """
    В режиме отладки Django обслуживает статические и медиа файлы напрямую.

    Это позволяет в процессе разработки:
    - Просматривать загруженные изображения инструментов
    - Доступ к CSS, JavaScript и другим статическим файлам
    - Тестировать функциональность загрузки файлов без настройки веб-сервера

    В продакшн-режиме эти функции должен выполнять веб-сервер (nginx, Apache)

    Сейчас для простоты я всё запускаю в дебаг-тру. И так тяжко искать ошибки
    """
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

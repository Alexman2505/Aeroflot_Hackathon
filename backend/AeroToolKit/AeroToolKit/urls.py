"""
Главный модуль маршрутизации Django проекта.

Определяет основные URL-шаблоны приложения и включает маршруты из других приложений.
Обеспечивает обслуживание статических и медиа файлов в режиме разработки.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

# Основные URL-шаблоны приложения
urlpatterns = [
    # Административная панель Django
    path('admin/', admin.site.urls),
    # Маршруты аутентификации и пользователей
    path('auth/', include('users.urls', namespace='users')),
    # Стандартные маршруты аутентификации Django (логин, логаут, сброс пароля и т.д.)
    path('auth/', include('django.contrib.auth.urls')),
    # API версии 1 для взаимодействия с фронтендом и мобильными приложениями
    path('api/v1/', include('api.urls')),
    # Маршруты для страниц команды и информации о проекте
    path('team/', include('team.urls', namespace='about')),
    # Основное приложение - инструменты (главная страница и функционал)
    path('', include('instruments.urls', namespace='instruments')),
    # Редиректы для совместимости со стандартными URL Django аутентификации
    path(
        'accounts/login/',
        RedirectView.as_view(url='/auth/login/', permanent=True),
    ),
    path(
        'accounts/logout/',
        RedirectView.as_view(url='/auth/logout/', permanent=True),
    ),
]

# Пользовательские обработчики ошибок
handler404 = 'core.views.page_not_found'  # Обработчик страницы 404 Not Found
handler403 = (
    'core.views.csrf_failure'  # Обработчик ошибки CSRF (403 Forbidden)
)

# Конфигурация для режима разработки
# В продакшене статические и медиа файлы должны обслуживаться веб-сервером, но у меня всё в дебаг true запускается
if settings.DEBUG:
    # Обслуживание статических файлов (CSS, JavaScript, изображения)
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )

    # Обслуживание медиа файлов (загруженные пользователями изображения, документы)
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

    # Интеграция Django Debug Toolbar для отладки приложения
    import debug_toolbar

    urlpatterns += (path('__debug__/', include(debug_toolbar.urls)),)

"""image_service URL Configuration

Конфигурация URL для Django приложения Image Service.

Этот модуль определяет маршрутизацию URL для приложения фотосервиса,
включая административный интерфейс, API endpoints и обслуживание медиафайлов.

Архитектура:
- Админка: /admin/ - Панель администратора Django
- API endpoints: /api/ - Маршруты API для обработки фото
- Медиафайлы: /media/ - Обслуживание статических медиафайлов
- Документация API: /api/docs/ - Интерактивная документация Swagger/ReDoc

Примеры URL паттернов:
Функциональные views
    1. Добавить импорт: from my_app import views
    2. Добавить URL: path('', views.home, name='home')
Класс-баsed views
    1. Добавить импорт: from other_app.views import Home
    2. Добавить URL: path('', Home.as_view(), name='home')
Включение другого URLconf
    1. Импортировать include(): from django.urls import include, path
    2. Добавить URL: path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

"""
Конфигурация Schema View для интерактивной документации API.

Предоставляет интерфейсы Swagger UI и ReDoc для изучения и тестирования
API endpoints Image Service.

Возможности:
- Автогенерация документации API из Django REST Framework views
- Интерактивный интерфейс тестирования API
- Поддержка аутентификации по токенам
- Информация о версионировании API
"""
schema_view = get_schema_view(
    openapi.Info(
        title="Image Service API",
        default_version='v1',
        description="""
        Документация API Image Service

        Этот сервис предоставляет возможности обработки и загрузки фотографий
        для системы AeroToolKit.

        ## Основные возможности
        - Многошаговый процесс загрузки изображений
        - Управление токенами аутентификации
        - Асинхронная обработка изображений через Celery
        - Интеграция с основным бэкендом AeroToolKit

        ## Аутентификация
        API использует Token Authentication:
        `Authorization: Token ********`

        ## Процесс работы
        1. Аутентификация пользователя через основной бэкенд
        2. Загрузка изображений с метаданными
        3. Асинхронная обработка изображений
        4. Получение результатов обработки

        ## Доступные endpoints
        - `GET /` - Главный интерфейс загрузки фото
        - `POST /` - Обработка загрузки изображений и аутентификации
        - `GET /clear-session/` - Выход и очистка сессии

        Для документации основного API бэкенда посетите AeroToolKit API docs.
        """,
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="support@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

"""
URL паттерны для приложения Image Service.

Определяет все доступные маршруты и соответствующие обработчики views.
Организованы по функциональности и уровню доступа.

Структура паттернов:
- Административные маршруты (admin/)
- Маршруты документации API (api/docs/)
- Маршруты API приложения (api/)
- Обслуживание медиафайлов (media/)
"""
urlpatterns = [
    # Интерфейс администратора Django
    path('admin/', admin.site.urls),
    # Интерактивная документация API
    path(
        'api/docs/swagger/',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui',
    ),
    path(
        'api/docs/redoc/',
        schema_view.with_ui('redoc', cache_timeout=0),
        name='schema-redoc',
    ),
    path(
        'api/docs/json/',
        schema_view.without_ui(cache_timeout=0),
        name='schema-json',
    ),
    # Маршруты API приложения
    path('', include('api.urls')),
]

"""
Конфигурация обслуживания медиафайлов для разработки.

Обслуживает загруженные медиафайлы во время разработки. В продакшене
это должно обрабатываться выделенным веб-сервером (nginx, Apache).

Важно для безопасности:
- Используйте только в среде разработки
- В продакшене настройте веб-сервер для обслуживания медиафайлов
- Рассмотрите использование CDN для медиафайлов в продакшене
"""
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

"""
Сводка доступных URL:

Сервер разработки:
- Админка: http://localhost:8001/admin/
- Swagger UI: http://localhost:8001/api/docs/swagger/
- ReDoc документация: http://localhost:8001/api/docs/redoc/
- JSON схема: http://localhost:8001/api/docs/json/
- Главное приложение: http://localhost:8001/
- Медиафайлы: http://localhost:8001/media/

Для продакшена:
- Используйте настройки для конкретного окружения для DEBUG режима
- Настройте правильное обслуживание медиафайлов в продакшене
- Настройте reverse proxy для документации API если нужно
- Реализуйте ограничение запросов и security headers
"""

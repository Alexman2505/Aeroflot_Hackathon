from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from .views import (
    obtain_auth_token_csrf_exempt,
    ToolViewSet,
    InstrumentViewSet,
)

# Инициализация маршрутизатора для автоматической генерации URL patterns
router = DefaultRouter()

# Регистрация ViewSet'ов в маршрутизаторе
router.register(r'tools', ToolViewSet, basename='tool')
router.register(r'instruments', InstrumentViewSet, basename='instrument')

# Конфигурация схемы OpenAPI для автоматической генерации документации
schema_view = get_schema_view(
    openapi.Info(
        title="AeroToolKit API",
        default_version='v1',
        description=(
            "API для системы управления инструментами AeroToolKit. "
            "Предоставляет endpoints для работы с инструментами, "
            "аутентификации пользователей и анализа изображений с помощью YOLO."
        ),
        contact=openapi.Contact(email="test@test.ru"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# Основные URL patterns приложения
urlpatterns = [
    # Включение автоматически сгенерированных URL от маршрутизатора
    path('', include(router.urls)),
    # Endpoint для получения аутентификационного токена (CSRF-экземптный)
    path(
        'api-token-auth/', obtain_auth_token_csrf_exempt, name='api-token-auth'
    ),
]

# URL patterns для документации API
urlpatterns += [
    # Swagger UI - интерактивная документация API
    path(
        'swagger/',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui',
    ),
    # ReDoc - альтернативный вариант документации API
    path(
        'redoc/',
        schema_view.with_ui('redoc', cache_timeout=0),
        name='schema-redoc',
    ),
]

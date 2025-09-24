from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ToolViewSet, upload_image_api
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.urls import path
from rest_framework.authtoken import views

router = DefaultRouter()
router.register(r'tools', ToolViewSet, basename='tool')

schema_view = get_schema_view(
    openapi.Info(
        title="AeroToolKit API",
        default_version='v1',
        description="Документация для приложения api проекта AeroToolKit",
        # terms_of_service="URL страницы с пользовательским соглашением",
        contact=openapi.Contact(email="test@test.ru"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', include(router.urls)),
    path('api-token-auth/', views.obtain_auth_token),
    path('upload/', upload_image_api, name='upload-image'),
]

# для документации свагера
urlpatterns += [
    path(
        'swagger<format>/',
        schema_view.without_ui(cache_timeout=0),
        name='schema-json',
    ),
    path(
        'swagger/',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui',
    ),
    path(
        'redoc/',
        schema_view.with_ui('redoc', cache_timeout=0),
        name='schema-redoc',
    ),
]
SWAGGER_SETTINGS = {
    'LOGIN_URL': '/auth/login/',
    'LOGOUT_URL': '/auth/logout/',
    'USE_SESSION_AUTH': True,
}

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('users.urls', namespace='users')),
    path('auth/', include('django.contrib.auth.urls')),
    path('api/v1/', include('api.urls')),
    path('team/', include('team.urls', namespace='about')),
    path('', include('instruments.urls', namespace='instruments')),
    path(
        'accounts/login/',
        RedirectView.as_view(url='/auth/login/', permanent=True),
    ),
    path(
        'accounts/logout/',
        RedirectView.as_view(url='/auth/logout/', permanent=True),
    ),
]

handler404 = 'core.views.page_not_found'
handler403 = 'core.views.csrf_failure'

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
    import debug_toolbar

    urlpatterns += (path('__debug__/', include(debug_toolbar.urls)),)

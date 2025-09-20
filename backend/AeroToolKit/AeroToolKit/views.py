from django.http import HttpResponse


def home_page(request):
    return HttpResponse(
        """
        <h1>🚀 AeroToolKit API</h1>
        <p>Добро пожаловать в систему идентификации гаечных ключей!</p>
        <ul>
            <li><a href="/api/">API Root</a></li>
            <li><a href="/api/tools/">Tools API</a></li>
            <li><a href="/admin/">Admin Panel</a></li>
        </ul>
    """
    )

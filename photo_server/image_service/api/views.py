import os
import uuid
import requests
from django.shortcuts import render, redirect
from django.utils import timezone
from django.conf import settings
from .tasks import send_single_image


def index(request):
    """
    Главная view-функция приложения для многошаговой обработки изображений.

    Обрабатывает три основных сценария:
    1. POST-запрос с данными авторизации
    2. POST-запрос с загруженными изображениями
    3. GET-запрос от авторизованного пользователя

    Args:
        request: Объект HTTP-запроса от Django

    Returns:
        HttpResponse: Отрендеренный шаблон с контекстом данных
    """
    context = {
        'current_timestamp': timezone.now().isoformat(),
        'step': 'auth',
        'success_count': 0,
        'error_count': 0,
        'images_count': 0,
    }

    if request.method == 'POST':
        context = check_step(request, context)
    elif 'aerotoolkit_token' in request.session:
        context = handle_authenticated_user(request, context)

    return render(request, 'api/index.html', context)


def check_step(request, context):
    """
    Анализирует POST-запрос и определяет текущий шаг.

    Проверяет наличие ключевых параметров в запросе чтобы определить:
    - Авторизация (наличие username и password)
    - Загрузка изображений (наличие images и api_token)

    Args:
        request: Объект HTTP-запроса
        context: Текущий контекст шаблона

    Returns:
        dict: Обновленный контекст после обработки соответствующего шага
    """
    # Шаг авторизации
    if 'username' in request.POST and 'password' in request.POST:
        context = handle_auth_step(request, context)

    # Шаг загрузки изображений
    elif 'images' in request.FILES and 'api_token' in request.POST:
        context = handle_image_upload(request, context)

    return context


def handle_auth_step(request, context):
    """
    Обрабатывает шаг авторизации пользователя.

    Получает логин и пароль из POST-запроса, аутентифицирует пользователя
    через внешнее API AeroToolKit. При успешной авторизации сохраняет токен
    в сессии и переключает контекст на шаг загрузки файлов.

    Args:
        request: Объект HTTP-запроса с данными авторизации
        context: Текущий контекст шаблона

    Returns:
        dict: Обновленный контекст с результатом авторизации
    """
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '').strip()

    token = get_auth_token(username, password)

    if token:
        request.session['aerotoolkit_token'] = token
        request.session['sender_name'] = username
        context['step'] = 'upload'
        context['token'] = token
        context['username'] = username
    else:
        context['step'] = 'auth'
        context['error'] = 'Ошибка авторизации: неверный логин или пароль'

    return context


def handle_image_upload(request, context):
    """
    Асинхронная обработка пакета изображений.

    Сохраняет загруженные файлы во временное хранилище и запускает
    фоновые Celery задачи для обработки каждого изображения отдельно.
    Возвращает пользователю мгновенный ответ с ID задач для отслеживания.

    Args:
        request: Объект HTTP-запроса с файлами изображений
        context: Текущий контекст шаблона

    Returns:
        dict: Контекст с информацией о запущенных задачах
    """
    token = request.POST.get('api_token', '').strip()
    name = request.session.get('sender_name', '')
    image_files = request.FILES.getlist('images')
    expected_objects = request.POST.get('expected_objects', '11')
    expected_confidence = request.POST.get('expected_confidence', '0.90')

    if token and name and image_files:
        # Сохраняем файлы во временное хранилище
        temp_file_paths = []

        for image_file in image_files:
            file_extension = os.path.splitext(image_file.name)[1]
            temp_filename = f"{uuid.uuid4().hex}{file_extension}"
            temp_file_path = os.path.join(
                settings.TEMP_UPLOAD_DIR, temp_filename
            )

            with open(temp_file_path, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)

            temp_file_paths.append(temp_file_path)

        # Подготавливаем данные для задачи
        user_data = {
            'name': name,
            'expected_objects': expected_objects,
            'expected_confidence': expected_confidence,
        }

        # Запускаем отдельные задачи для каждого файла
        task_ids = []

        for file_path in temp_file_paths:
            task = send_single_image.delay(file_path, token, user_data)
            task_ids.append(task.id)

        # Мгновенный ответ пользователю
        context.update(
            {
                'step': 'processing',
                'task_ids': task_ids,
                'images_count': len(image_files),
                'submitted': True,
                'sender_name': name,
                'expected_objects': expected_objects,
                'expected_confidence': expected_confidence,
            }
        )

    else:
        context['step'] = 'upload'
        context['error'] = 'Ошибка: заполните все обязательные поля'

    return context


def handle_authenticated_user(request, context):
    """
    Обрабатывает запрос от уже авторизованного пользователя.

    Если пользователь уже прошел авторизацию и токен сохранен в сессии,
    переключает контекст непосредственно на шаг загрузки файлов.

    Args:
        request: Объект HTTP-запроса
        context: Текущий контекст шаблона

    Returns:
        dict: Контекст с настройками для шага загрузки
    """
    context['step'] = 'upload'
    context['token'] = request.session['aerotoolkit_token']
    context['username'] = request.session.get('sender_name', '')
    return context


def clear_session(request):
    """
    Очищает сессию пользователя и выполняет redirect на главную страницу.

    Удаляет все данные аутентификации из сессии, возвращая пользователя
    к начальному шагу авторизации.

    Args:
        request: Объект HTTP-запроса

    Returns:
        HttpResponseRedirect: Перенаправление на главную страницу
    """
    if 'aerotoolkit_token' in request.session:
        del request.session['aerotoolkit_token']
    if 'sender_name' in request.session:
        del request.session['sender_name']
    return redirect('index')


def get_auth_token(username, password, auth_url=None):
    """
    Выполняет аутентификацию пользователя через API AeroToolKit.

    Отправляет запрос к endpoint /api/v1/api-token-auth/ для получения
    токена аутентификации по логину и паролю.

    Args:
        username: Логин пользователя
        password: Пароль пользователя
        auth_url: URL endpoint аутентификации. Если не указан,
                 берется из settings.AEROTOOLKIT_AUTH_URL

    Returns:
        str|None: Токен аутентификации при успехе, None при ошибке
    """
    if auth_url is None:
        auth_url = settings.AEROTOOLKIT_AUTH_URL

    payload = {'username': username, 'password': password}

    try:
        response = requests.post(
            auth_url,
            json=payload,
            timeout=10,
            headers={'Content-Type': 'application/json'},
        )

        if response.status_code == 200:
            return response.json().get('token')
        else:
            return None

    except requests.exceptions.RequestException:
        return None

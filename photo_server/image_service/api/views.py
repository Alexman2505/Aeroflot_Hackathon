import base64
import requests
from django.shortcuts import render, redirect
from django.utils import timezone
from django.conf import settings


def index(request):
    """
    Главная view-функция приложения для многошаговой обработки изображений.

    Обрабатывает три основных сценария:
    1. POST-запрос с данными авторизации
    2. POST-запрос с загруженными изображениями
    3. GET-запрос от авторизованного пользователя

    Args:
        request (HttpRequest): Объект HTTP-запроса от Django

    Returns:
        HttpResponse: Отрендеренный шаблон с контекстом данных
    """
    context = {
        'current_timestamp': timezone.now().isoformat(),
        'step': 'auth',  # По умолчанию показываем форму авторизации
        'success_count': 0,  # Инициализируем по умолчанию
        'error_count': 0,  # Инициализируем по умолчанию
        'images_count': 0,  # Инициализируем по умолчанию
    }
    # при пост-запросе пытаемся выбрать шаг работы сайта
    if request.method == 'POST':
        context = check_step(request, context)
    elif 'aerotoolkit_token' in request.session:
        context = handle_authenticated_user(request, context)

    return render(request, 'api/index.html', context)


def check_step(request, context):
    """
    Анализирует POST-запрос и определяет текущий шаг workflow.

    Проверяет наличие ключевых параметров в запросе чтобы определить:
    - Авторизация (наличие username и password)
    - Загрузка изображений (наличие images и api_token)

    Args:
        request (HttpRequest): Объект HTTP-запроса
        context (dict): Текущий контекст шаблона

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
        request (HttpRequest): Объект HTTP-запроса с данными авторизации
        context (dict): Текущий контекст шаблона

    Returns:
        dict: Обновленный контекст с результатом авторизации
    """
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '').strip()

    token = get_auth_token(username, password)
    if token:
        # Сохраняем токен в сессии и переходим к шагу загрузки файлов
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
    Обрабатывает загрузку и отправку изображений на внешний API.
    """
    token = request.POST.get('api_token', '').strip()
    name = request.session.get('sender_name', '')
    image_files = request.FILES.getlist('images')

    if token and name and image_files:
        processed_images = []
        success_count = 0
        delivery_failed_count = 0  # Файл не доставлен
        rejected_count = 0  # Файл доставлен, но отвергнут (4xx)
        server_error_count = 0  # Файл доставлен, сервер упал (5xx)

        for image_file in image_files:
            # Кодируем каждое изображение в base64
            image_data = image_file.read()
            base64_string = base64.b64encode(image_data).decode('utf-8')
            image_format = (
                image_file.name.split('.')[-1]
                if '.' in image_file.name
                else 'jpeg'
            )
            full_base64_string = (
                f"data:image/{image_format};base64,{base64_string}"
            )

            # Отправляем на внешний API
            result = send_to_aerotoolkit_api(name, full_base64_string, token)

            if result == "success":
                success_count += 1
            elif result == "delivered_but_rejected":
                rejected_count += 1
            elif result == "delivered_but_server_error":
                server_error_count += 1
            else:  # delivery_failed
                delivery_failed_count += 1

            processed_images.append(
                {
                    'filename': image_file.name,
                    'full_base64_string': full_base64_string,
                    'base64_string': base64_string,
                    'format': image_format,
                    'size': len(image_data),
                }
            )

        # Берем первое изображение для отображения на сайте
        first_image = processed_images[0] if processed_images else None

        context.update(
            {
                'step': 'results',
                'submitted': True,
                'sender_name': name,
                'images_count': len(processed_images),
                'success_count': success_count,
                'delivery_failed_count': delivery_failed_count,
                'rejected_count': rejected_count,
                'server_error_count': server_error_count,
                'first_image': first_image,
                'full_base64_string': (
                    first_image['full_base64_string'] if first_image else ''
                ),
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
        request (HttpRequest): Объект HTTP-запроса
        context (dict): Текущий контекст шаблона

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
        request (HttpRequest): Объект HTTP-запроса

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
        username (str): Логин пользователя
        password (str): Пароль пользователя
        auth_url (str, optional): URL endpoint аутентификации. Если не указан,
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
            print(
                f"Ошибка аутентификации: {response.status_code} - {response.text}"
            )
            return None

    except requests.exceptions.RequestException as e:
        print(f"Ошибка подключения к серверу аутентификации: {e}")
        return None


def send_to_aerotoolkit_api(name, full_base64_string, token):
    """
    Отправляет одно изображение на API AeroToolKit.
    """
    text = (
        f"Фотография автоматически загружена через систему фотофиксации.\n"
        f"Сотрудник, отправивший фотографию: {name}\n"
        f"Локальное время отправки с сервера фотофиксации PhotoService: {timezone.now().strftime('%d.%m.%Y %H:%M:%S')}"
    )

    payload = {
        "text": text,
        "full_base64_string": full_base64_string,
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {token}',
    }

    try:
        response = requests.post(
            settings.AEROTOOLKIT_API_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )

        print(f"Статус ответа: {response.status_code}")
        print(f"Текст ответа: {response.text}")

        # ПРАВИЛЬНАЯ логика обработки статусов:
        if response.status_code in [200, 201]:
            # Успех - файл доставлен И обработан
            print("Изображение успешно отправлено и распознано")
            return "success"

        elif 400 <= response.status_code < 500:
            # Клиентские ошибки - файл ДОСТАВЛЕН, но сервер отверг запрос
            # (неправильный токен, невалидные данные, нет прав и т.д.)
            print(
                f"Файл доставлен, но сервер отверг запрос: {response.status_code}"
            )
            return "delivered_but_rejected"

        elif response.status_code >= 500:
            # Серверные ошибки - файл ДОСТАВЛЕН, но сервер упал
            print(
                f"Файл доставлен, но серверная ошибка: {response.status_code}"
            )
            return "delivered_but_server_error"

        else:
            # Другие статусы (редиректы и т.д.)
            print(f"Неожиданный статус: {response.status_code}")
            return "delivery_failed"

    except requests.exceptions.RequestException as e:
        # Сетевые ошибки - файл НЕ доставлен
        print(f"Ошибка подключения (файл не доставлен): {e}")
        return "delivery_failed"

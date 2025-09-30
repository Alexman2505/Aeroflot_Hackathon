# import base64
import os
import uuid
import requests
from django.shortcuts import render, redirect
from django.utils import timezone
from django.conf import settings
from .tasks import process_image_batch
import time


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
    Анализирует POST-запрос и определяет текущий шаг.

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
    Асинхронная обработка изображений.
    """
    start_total = time.time()
    print(f"[{time.time()}] НАЧАЛО handle_image_upload", flush=True)

    token = request.POST.get('api_token', '').strip()
    name = request.session.get('sender_name', '')
    image_files = request.FILES.getlist('images')
    expected_objects = request.POST.get('expected_objects', '11')
    expected_confidence = request.POST.get('expected_confidence', '0.90')
    start_time = time.time()

    print(f"Получено файлов: {len(image_files)}", flush=True)

    if token and name and image_files:
        # Сохраняем файлы во временное хранилище
        temp_file_paths = []
        start_save = time.time()
        for i, image_file in enumerate(image_files):
            file_start = time.time()
            file_extension = os.path.splitext(image_file.name)[1]
            temp_filename = f"{uuid.uuid4().hex}{file_extension}"
            temp_file_path = os.path.join(
                settings.TEMP_UPLOAD_DIR, temp_filename
            )

            with open(temp_file_path, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)

            temp_file_paths.append(temp_file_path)

            file_time = time.time() - file_start
            print(f"Файл {i+1} сохранен за {file_time:.2f}сек", flush=True)

        save_time = time.time() - start_save
        print(f"ВСЕ файлы сохранены за {save_time:.2f}сек", flush=True)

        # Подготавливаем данные для задачи
        user_data = {
            'name': name,
            'expected_objects': expected_objects,
            'expected_confidence': expected_confidence,
        }

        print(f" Запускаем Celery задачу...", flush=True)
        start_celery = time.time()

        # запускаем фоновую задачу без ожидания
        task = process_image_batch.delay(
            file_paths=temp_file_paths, token=token, user_data=user_data
        )

        celery_time = time.time() - start_celery
        print(
            f" Celery задача запущена за {celery_time:.2f}сек, ID: {task.id}",
            flush=True,
        )

        # мгновенный ответ пользователю
        context.update(
            {
                'step': 'processing',  # Новый шаг "обработка"
                'task_id': task.id,  # Сохраняем ID задачи
                'images_count': len(image_files),
                'submitted': True,
                'sender_name': name,
                'expected_objects': expected_objects,
                'expected_confidence': expected_confidence,
            }
        )

        total_time = time.time() - start_total
        print(
            f"ОБЩЕЕ ВРЕМЯ handle_image_upload: {total_time:.2f}сек",
            flush=True,
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


# def send_to_aerotoolkit_api_binary(
#     name,
#     image_file,
#     token,
#     expected_objects=None,
#     expected_confidence=None,
# ):
#     """
#     Отправляет бинарный файл на API AeroToolKit.
#     """
#     text = (
#         f"Фотография автоматически загружена через систему фотофиксации.\n"
#         f"Сотрудник: {name}\n"
#         f"Время отправки: {timezone.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
#         f"Файл: {image_file.name}\n"
#         f"Ожидаемое количество: {int(expected_objects)}\n"
#         f"Уверенность: {float(expected_confidence)}"
#     )

#     # Подготавливаем multipart/form-data
#     files = {'image': (image_file.name, image_file.file, 'image/jpeg')}

#     data = {
#         'text': text,
#         'expected_objects': expected_objects,
#         'expected_confidence': expected_confidence,
#         'filename': image_file.name,
#     }

#     headers = {
#         'Authorization': f'Token {token}',
#     }

#     try:
#         response = requests.post(
#             settings.AEROTOOLKIT_API_URL,
#             files=files,
#             data=data,
#             headers=headers,
#             timeout=30,
#         )

#         if response.status_code in [200, 201]:
#             return "success"
#         elif 400 <= response.status_code < 500:
#             return "delivered_but_rejected"
#         elif response.status_code >= 500:
#             return "delivered_but_server_error"
#         else:
#             return "delivery_failed"

#     except requests.exceptions.RequestException as e:
#         print(f"Ошибка подключения: {e}")
#         return "delivery_failed"

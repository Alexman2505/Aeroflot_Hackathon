import os
import uuid
import requests
from django.shortcuts import render, redirect
from django.utils import timezone
from django.conf import settings
from .tasks import process_image_batch
import time
from .tasks import send_single_image


def index(request):
    """
    Главная view-функция приложения для многошаговой обработки изображений.
    """
    context = {
        'current_timestamp': timezone.now().isoformat(),
        'step': 'auth',
        'success_count': 0,
        'error_count': 0,
        'images_count': 0,
    }

    print(f"[{time.time()}] === НАЧАЛО index ===", flush=True)
    print(f"[{time.time()}] Метод запроса: {request.method}", flush=True)

    if request.method == 'POST':
        print(f"[{time.time()}] Обрабатываем POST запрос", flush=True)
        context = check_step(request, context)
    elif 'aerotoolkit_token' in request.session:
        print(f"[{time.time()}] Пользователь уже авторизован", flush=True)
        context = handle_authenticated_user(request, context)
    else:
        print(f"[{time.time()}] Показываем форму авторизации", flush=True)

    print(
        f"[{time.time()}] === КОНЕЦ index, шаг: {context['step']} ===",
        flush=True,
    )
    return render(request, 'api/index.html', context)


def check_step(request, context):
    """
    Анализирует POST-запрос и определяет текущий шаг.
    """
    print(f"[{time.time()}] check_step: проверяем параметры POST", flush=True)

    # Шаг авторизации
    if 'username' in request.POST and 'password' in request.POST:
        print(
            f"[{time.time()}] Обнаружены username/password - шаг авторизации",
            flush=True,
        )
        context = handle_auth_step(request, context)

    # Шаг загрузки изображений
    elif 'images' in request.FILES and 'api_token' in request.POST:
        print(
            f"[{time.time()}] Обнаружены images/api_token - шаг загрузки",
            flush=True,
        )
        context = handle_image_upload(request, context)
    else:
        print(f"[{time.time()}] Неизвестный шаг POST", flush=True)
        print(
            f"[{time.time()}] POST keys: {list(request.POST.keys())}",
            flush=True,
        )
        print(
            f"[{time.time()}] FILES keys: {list(request.FILES.keys())}",
            flush=True,
        )

    return context


def handle_auth_step(request, context):
    """
    Обрабатывает шаг авторизации пользователя.
    """
    print(f"[{time.time()}] handle_auth_step: начало", flush=True)

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '').strip()

    print(
        f"[{time.time()}] Получены credentials: username={username}",
        flush=True,
    )

    auth_start = time.time()
    token = get_auth_token(username, password)
    auth_time = time.time() - auth_start

    print(
        f"[{time.time()}] Аутентификация заняла {auth_time:.3f}сек", flush=True
    )

    if token:
        print(
            f"[{time.time()}] Аутентификация УСПЕШНА, токен получен",
            flush=True,
        )
        request.session['aerotoolkit_token'] = token
        request.session['sender_name'] = username
        context['step'] = 'upload'
        context['token'] = token
        context['username'] = username
    else:
        print(f"[{time.time()}] Аутентификация ПРОВАЛЕНА", flush=True)
        context['step'] = 'auth'
        context['error'] = 'Ошибка авторизации: неверный логин или пароль'

    print(
        f"[{time.time()}] handle_auth_step: конец, шаг: {context['step']}",
        flush=True,
    )
    return context


def handle_image_upload(request, context):
    """
    Асинхронная обработка изображений - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ.
    """
    start_total = time.time()
    print(
        f"[{time.time()}]  НАЧАЛО handle_image_upload (ОПТИМИЗИРОВАННАЯ) ",
        flush=True,
    )

    token = request.POST.get('api_token', '').strip()
    name = request.session.get('sender_name', '')
    image_files = request.FILES.getlist('images')
    expected_objects = request.POST.get('expected_objects', '11')
    expected_confidence = request.POST.get('expected_confidence', '0.90')

    print(f"[{time.time()}] Получены параметры:", flush=True)
    print(f"[{time.time()}]   token: {'ЕСТЬ' if token else 'НЕТ'}", flush=True)
    print(f"[{time.time()}]   name: {name}", flush=True)
    print(f"[{time.time()}]   files: {len(image_files)}", flush=True)
    print(
        f"[{time.time()}]   expected_objects: {expected_objects}", flush=True
    )
    print(
        f"[{time.time()}]   expected_confidence: {expected_confidence}",
        flush=True,
    )

    if token and name and image_files:
        # Сохраняем файлы во временное хранилище
        temp_file_paths = []
        start_save = time.time()

        print(
            f"[{time.time()}] Начинаем сохранение {len(image_files)} файлов...",
            flush=True,
        )

        for i, image_file in enumerate(image_files):
            file_start = time.time()
            file_extension = os.path.splitext(image_file.name)[1]
            temp_filename = f"{uuid.uuid4().hex}{file_extension}"
            temp_file_path = os.path.join(
                settings.TEMP_UPLOAD_DIR, temp_filename
            )

            print(
                f"[{time.time()}] Сохраняем файл {i+1}: {image_file.name} -> {temp_filename}",
                flush=True,
            )

            with open(temp_file_path, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)

            temp_file_paths.append(temp_file_path)

            file_time = time.time() - file_start
            print(
                f"[{time.time()}] Файл {i+1} сохранен за {file_time:.3f}сек",
                flush=True,
            )

        save_time = time.time() - start_save
        print(
            f"[{time.time()}]  ВСЕ {len(image_files)} файлов сохранены за {save_time:.3f}сек",
            flush=True,
        )

        # Подготавливаем данные для задачи
        user_data = {
            'name': name,
            'expected_objects': expected_objects,
            'expected_confidence': expected_confidence,
        }

        print(
            f"[{time.time()}] Подготавливаем user_data: {user_data}",
            flush=True,
        )

        # ОПТИМИЗИРОВАННЫЙ ЗАПУСК CELERY ЗАДАЧ
        print(
            f"[{time.time()}]  ОПТИМИЗИРОВАННЫЙ ЗАПУСК CELERY ЗАДАЧ...",
            flush=True,
        )
        print(
            f"[{time.time()}] Отправляем {len(temp_file_paths)} задач send_single_image напрямую",
            flush=True,
        )

        start_celery = time.time()
        task_ids = []

        # ДИАГНОСТИКА CELERY
        print(
            f"[{time.time()}] 1. Время перед импортом Celery app", flush=True
        )

        from image_service.celery import app as celery_app

        print(f"[{time.time()}] 2. Celery app импортирован", flush=True)
        print(
            f"[{time.time()}] 3. Broker URL: {celery_app.conf.broker_url}",
            flush=True,
        )

        # Проверка подключения к брокеру
        conn_check_start = time.time()
        try:
            with celery_app.connection() as conn:
                conn.ensure_connection(max_retries=1)
            conn_time = time.time() - conn_check_start
            print(
                f"[{time.time()}] 4.  Подключение к брокеру OK: {conn_time:.3f}сек",
                flush=True,
            )
        except Exception as e:
            conn_time = time.time() - conn_check_start
            print(
                f"[{time.time()}] 4.  ОШИБКА подключения к брокеру: {e}, время: {conn_time:.3f}сек",
                flush=True,
            )

        # ОТПРАВКА ЗАДАЧ НАПРЯМУЮ - КАЖДОГО ФАЙЛА ОТДЕЛЬНО
        tasks_start = time.time()
        print(
            f"[{time.time()}] 5. Начинаем отправку {len(temp_file_paths)} отдельных задач...",
            flush=True,
        )

        for i, file_path in enumerate(temp_file_paths):
            task_single_start = time.time()
            print(
                f"[{time.time()}]   Отправляем задачу для файла {i+1}: {os.path.basename(file_path)}",
                flush=True,
            )

            try:
                # Отправляем каждую задачу отдельно
                task = send_single_image.delay(file_path, token, user_data)
                task_ids.append(task.id)
                task_single_time = time.time() - task_single_start
                print(
                    f"[{time.time()}]    Задача {i+1} отправлена за {task_single_time:.3f}сек, ID: {task.id}",
                    flush=True,
                )
            except Exception as e:
                task_single_time = time.time() - task_single_start
                print(
                    f"[{time.time()}]    Ошибка отправки задачи {i+1}: {e}, время: {task_single_time:.3f}сек",
                    flush=True,
                )

        tasks_total_time = time.time() - tasks_start
        print(
            f"[{time.time()}] 6.  ВСЕ {len(task_ids)} задач отправлены за {tasks_total_time:.3f}сек",
            flush=True,
        )

        celery_total_time = time.time() - start_celery
        print(
            f"[{time.time()}] 7. ВСЯ Celery операция заняла: {celery_total_time:.3f}сек",
            flush=True,
        )
        print(f"[{time.time()}] 8. ID всех задач: {task_ids}", flush=True)

        # Мгновенный ответ пользователю
        context.update(
            {
                'step': 'processing',
                'task_ids': task_ids,  # Теперь передаем список ID
                'images_count': len(image_files),
                'submitted': True,
                'sender_name': name,
                'expected_objects': expected_objects,
                'expected_confidence': expected_confidence,
            }
        )

    else:
        print(
            f"[{time.time()}]  Ошибка: не все обязательные поля заполнены",
            flush=True,
        )
        context['step'] = 'upload'
        context['error'] = 'Ошибка: заполните все обязательные поля'

    total_time = time.time() - start_total
    print(
        f"[{time.time()}]  КОНЕЦ handle_image_upload: ОБЩЕЕ ВРЕМЯ {total_time:.3f}сек",
        flush=True,
    )
    print(f"[{time.time()}]  Итоговый шаг: {context['step']}", flush=True)

    return context


def handle_authenticated_user(request, context):
    """
    Обрабатывает запрос от уже авторизованного пользователя.
    """
    print(
        f"[{time.time()}] handle_authenticated_user: пользователь уже авторизован",
        flush=True,
    )
    context['step'] = 'upload'
    context['token'] = request.session['aerotoolkit_token']
    context['username'] = request.session.get('sender_name', '')
    return context


def clear_session(request):
    """
    Очищает сессию пользователя.
    """
    print(f"[{time.time()}] clear_session: очистка сессии", flush=True)
    if 'aerotoolkit_token' in request.session:
        del request.session['aerotoolkit_token']
    if 'sender_name' in request.session:
        del request.session['sender_name']
    return redirect('index')


def get_auth_token(username, password, auth_url=None):
    """
    Выполняет аутентификацию пользователя через API AeroToolKit.
    """
    print(
        f"[{time.time()}] get_auth_token: начало для пользователя {username}",
        flush=True,
    )

    if auth_url is None:
        auth_url = settings.AEROTOOLKIT_AUTH_URL

    payload = {'username': username, 'password': password}

    try:
        print(f"[{time.time()}] Отправляем запрос к {auth_url}", flush=True)
        response = requests.post(
            auth_url,
            json=payload,
            timeout=10,
            headers={'Content-Type': 'application/json'},
        )

        print(
            f"[{time.time()}] Получен ответ: статус {response.status_code}",
            flush=True,
        )

        if response.status_code == 200:
            token = response.json().get('token')
            print(f"[{time.time()}]  Токен получен успешно", flush=True)
            return token
        else:
            print(
                f"[{time.time()}]  Ошибка аутентификации: {response.status_code} - {response.text}",
                flush=True,
            )
            return None

    except requests.exceptions.RequestException as e:
        print(
            f"[{time.time()}]  Ошибка подключения к серверу аутентификации: {e}",
            flush=True,
        )
        return None

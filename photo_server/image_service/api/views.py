import base64
import requests
from django.shortcuts import render
from django.utils import timezone
from django.conf import settings


def index(request):
    """
    Основная view-функция для отображения главной страницы и обработки формы.

    Обрабатывает GET и POST запросы:
    - GET: отображает форму для загрузки изображений
    - POST: обрабатывает загруженные изображения, кодирует в base64 строку
    и отправляет json c этой строкой-картинкой на внешний API

    Args:
        request (HttpRequest): Объект HTTP-запроса

    Returns:
        HttpResponse: HTML-страница с формой или результатами обработки
    """
    context = {
        'current_timestamp': timezone.now().isoformat(),
    }

    if request.method == 'POST':
        name = request.POST.get('sender_name', '').strip()
        image_files = request.FILES.getlist('images')
        token = request.POST.get('api_token', '').strip()

        if name and image_files and token:
            processed_images = []
            success_count = 0
            error_count = 0

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

                # Отправляем на внешний API (без проверки результата)
                success = send_to_aerotoolkit_api(
                    name, full_base64_string, token
                )
                if success:
                    success_count += 1
                else:
                    error_count += 1

                processed_images.append(
                    {
                        'filename': image_file.name,
                        'full_base64_string': full_base64_string,
                        'base64_string': base64_string,
                        'format': image_format,
                        'size': len(image_data),
                    }
                )

            # Берем последнее изображение для отображения на сайте
            last_image = processed_images[-1] if processed_images else None

            context.update(
                {
                    'submitted': True,
                    'sender_name': name,
                    'images_count': len(processed_images),
                    'last_image': last_image,
                    'full_base64_string': (
                        last_image['full_base64_string'] if last_image else ''
                    ),
                }
            )

    return render(request, 'images/index.html', context)


def get_auth_token(username, password, auth_url=None):
    """
    Получает токен аутентификации с основного сервера AeroToolKit
    Args:
        username (str): имя пользователя заранее зарегистрированного на сервисе AeroToolKit.
        password (str): Пароль этого пользователя с сервиса AeroToolKit
        auth_url (str): Адрес API AeroToolKit, который выдает токены

    Returns:
        token (str): возвращает токен, полученный от AeroToolKit для последующей аутентификации

    """
    if auth_url is None:
        auth_url = settings.AEROTOOLKIT_AUTH_URL
    payload = {'username': username, 'password': password}

    try:
        response = requests.post(auth_url, json=payload, timeout=10)

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


def send_to_aerotoolkit_api(name, full_base64_string):
    """
    Отправляет изображение на API AeroToolKit с аутентификацией по токену
    Args:
        name (str): Идентификатор отправителя. Используется для аутентификации
                   на стороне принимающего сервиса. Содержит уникальный токен.

        full_base64_string (str): Полная data URL строка изображения в формате:
                                "data:image/<format>;base64,<encoded_data>"
                                Где:
                                - <format>: jpeg, png, gif, etc.
                                - <encoded_data>: бинарные данные изображения,
                                  закодированные в base64

        token (str): токен, полученный от
    """
    payload = {
        "sender": name,
        "timestamp": timezone.now().isoformat(),
        "full_base64_string": full_base64_string,
    }

    try:
        requests.post(
            settings.AEROTOOLKIT_API_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30,  # Можно увеличить для больших файлов
        )
    except:
        pass  # Бесшумная обработка ошибок


'''
для тестирования нашего апи на сервисе 'https://httpbin.org/post'
но сейчас эта функция отключена, т.к. сайт для тестирования подхватывается
автоматически из виртуального окружения env
кто хочет - разкомментируйте, чтобы в консоли видеть полученный ответ от
бесплатного апи httpbin. Он присылает обратно то, что ему отправили.
Так и проверяется работоспособность нашего сервиса
'''

# def send_to_external_api(name, full_base64_string):
#     """
#     Функция выполняет HTTP POST запрос к внешнему API https://httpbin.org/post,
#     который возвращает тот же json обратно для проверки работы сервиса.
#     """
#     import logging

#     logger = logging.getLogger(__name__)

#     # Упрощаем данные для теста - берем только первые 100 символов
#     test_image_string = (
#         full_base64_string[:100] + "..."
#         if len(full_base64_string) > 100
#         else full_base64_string
#     )

#     payload = {
#         "sender": name,
#         "timestamp": timezone.now().isoformat(),
#         "image_string": test_image_string,  # Тестовая короткая строка
#     }

#     print(" ДЕБАГ: Начинаем отправку...")
#     print(f" ДЕБАГ: API URL: 'https://httpbin.org/post'")
#     print(f" ДЕБАГ: Длина строки: {len(full_base64_string)} символов")

#     try:
#         # Тестовый запрос с коротким таймаутом
#         response = requests.post(
#             'https://httpbin.org/post',
#             json=payload,
#             headers={'Content-Type': 'application/json'},
#             timeout=30,  # Короткий таймаут для теста
#         )

#         print(f" УСПЕХ: Статус ответа: {response.status_code}")
#         print(
#             f" УСПЕХ: Ответ: {response.text[:200]}..."
#         )  # Первые 200 символов

#         return True

#     except requests.exceptions.Timeout:
#         print(" ТАЙМАУТ: Запрос превысил время ожидания")
#         return False
#     except requests.exceptions.ConnectionError as e:
#         print(f" ОШИБКА ПОДКЛЮЧЕНИЯ: {e}")
#         return False
#     except Exception as e:
#         print(f" НЕИЗВЕСТНАЯ ОШИБКА: {e}")
#         return False

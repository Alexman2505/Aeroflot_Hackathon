import base64
import requests
from django.shortcuts import render
from django.utils import timezone


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

        if name and image_files:
            processed_images = []

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
                send_to_external_api(name, full_base64_string)

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


##для отправки уже на наше апи на сервисе 'AeroToolKit/api'
##не забудь поменять строку на PythonAnywhere
def send_to_external_api(name, full_base64_string):
    """
    Функция выполняет HTTP POST запрос к внешнему API endpoint AeroToolKit,
    Основная цель - передача данных изображения в формате
    base64 для последующей обработки ML-моделью целевого сервиса.

    Args:
        name (str): Идентификатор отправителя. Используется для аутентификации
                   на стороне принимающего сервиса. Содержит уникальный токен.

        full_base64_string (str): Полная data URL строка изображения в формате:
                                "data:image/<format>;base64,<encoded_data>"
                                Где:
                                - <format>: jpeg, png, gif, etc.
                                - <encoded_data>: бинарные данные изображения,
                                  закодированные в base64
    """
    payload = {
        "sender": name,
        "timestamp": timezone.now().isoformat(),
        "full_base64_string": full_base64_string,
    }

    try:
        requests.post(
            # не забудь поменять строку на PythonAnywhere
            # на адрес api AeroToolKit куда json отправляем
            'https://AeroToolKit.org/api/post',
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30,  # Можно увеличить для больших файлов
        )
    except:
        pass  # Бесшумная обработка ошибок


## для тестирования апи на сервисе 'https://httpbin.org/post'
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

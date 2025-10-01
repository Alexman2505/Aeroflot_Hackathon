import os
import requests
from celery import shared_task
from django.utils import timezone
from django.conf import settings
import time


@shared_task
def send_single_image(temp_file_path, token, user_data):
    """
    Фоновая Celery задача для отправки одного изображения в основной бэкенд.

    Выполняет асинхронную отправку изображения в AeroToolKit API с полной
    информацией о сотруднике и параметрах обработки. Задача включает
    детальное логирование и обработку ошибок.

    Process Flow:
    1. Чтение временного файла изображения с диска
    2. Подготовка метаданных и текстового описания
    3. Отправка POST запроса в основной бэкенд
    4. Очистка временных файлов
    5. Детальное логирование времени выполнения

    Args:
        temp_file_path (str): Путь к временному файлу изображения на диске
        token (str): Аутентификационный токен для доступа к API бэкенда
        user_data (dict): Данные пользователя и параметры обработки:
            - name (str): Имя сотрудника
            - expected_objects (int): Ожидаемое количество объектов
            - expected_confidence (float): Порог уверенности распознавания

    Returns:
        dict: Результат выполнения задачи:
            - status (str): 'success' при успешной отправке, 'failed' при ошибке
            - filename (str): Имя обработанного файла
            - status_code (int): HTTP статус код ответа от API (только при success)
            - error (str): Сообщение об ошибке (только при failed)

    Raises:
        OSError: При проблемах чтения/удаления файлов
        requests.exceptions.RequestException: При ошибках сетевого запроса
        Exception: Любые другие неожиданные ошибки

    Example:
        >>> result = send_single_image.delay(
        ...     temp_file_path='/app/media/temp_uploads/image123.jpg',
        ...     token='9944b09199c6**********6dd0e4bbdfc6ee4b',
        ...     user_data={
        ...         'name': 'Иван Петров',
        ...         'expected_objects': 11,
        ...         'expected_confidence': 0.8
        ...     }
        ... )
    """
    task_start = time.time()
    filename = os.path.basename(temp_file_path)
    print(
        f"[{time.time()}] [Celery]  send_single_image ЗАПУЩЕН: {filename}",
        flush=True,
    )
    print(
        f"[{time.time()}] [Celery]   token: {'ЕСТЬ' if token else 'НЕТ'}",
        flush=True,
    )
    print(f"[{time.time()}] [Celery]   user_data: {user_data}", flush=True)

    try:
        # Читаем сохраненный файл
        read_start = time.time()
        print(f"[{time.time()}] [Celery] Читаем файл {filename}", flush=True)
        with open(temp_file_path, 'rb') as f:
            image_data = f.read()
        read_time = time.time() - read_start
        print(
            f"[{time.time()}] [Celery] Файл прочитан за {read_time:.3f}сек, размер: {len(image_data)} bytes",
            flush=True,
        )

        # Подготавливаем данные для отправки
        text = (
            f"Фотография автоматически загружена через систему фотофиксации.\n"
            f"Сотрудник: {user_data.get('name', 'Unknown')}\n"
            f"Время отправки: {timezone.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"Файл: {filename}\n"
            f"Ожидаемое количество: {user_data.get('expected_objects', 11)}\n"
            f"Уверенность: {user_data.get('expected_confidence', 0.9)}"
        )

        files = {'image': (filename, image_data, 'image/jpeg')}
        data = {
            'text': text,
            'expected_objects': user_data.get('expected_objects', 11),
            'expected_confidence': user_data.get('expected_confidence', 0.9),
            'filename': filename,
        }

        headers = {'Authorization': f'Token {token}'}

        print(
            f"[{time.time()}] [Celery] Отправляем запрос к {settings.AEROTOOLKIT_API_URL}",
            flush=True,
        )

        # Отправка на API
        send_start = time.time()
        response = requests.post(
            settings.AEROTOOLKIT_API_URL,
            files=files,
            data=data,
            headers=headers,
            timeout=60,
        )
        send_time = time.time() - send_start

        print(
            f"[{time.time()}] [Celery] Ответ получен за {send_time:.3f}сек, статус: {response.status_code}",
            flush=True,
        )

        # Очищаем временный файл
        cleanup_start = time.time()
        try:
            os.remove(temp_file_path)
            print(
                f"[{time.time()}] [Celery] Временный файл удален за {time.time()-cleanup_start:.3f}сек",
                flush=True,
            )
        except OSError as e:
            print(
                f"[{time.time()}] [Celery] Ошибка удаления файла: {e}",
                flush=True,
            )

        total_time = time.time() - task_start
        print(
            f"[{time.time()}] [Celery]  Файл ОТПРАВЛЕН: {filename}, общее время: {total_time:.3f}сек",
            flush=True,
        )

        return {
            'status': (
                'success' if response.status_code in [200, 201] else 'failed'
            ),
            'filename': filename,
            'status_code': response.status_code,
        }

    except Exception as e:
        error_time = time.time() - task_start
        print(
            f"[{time.time()}] [Celery]  ОШИБКА в send_single_image: {e}, время: {error_time:.3f}сек",
            flush=True,
        )

        # Очищаем временный файл в случае ошибки
        try:
            os.remove(temp_file_path)
            print(
                f"[{time.time()}] [Celery] Временный файл удален после ошибки",
                flush=True,
            )
        except OSError:
            pass

        return {
            'status': 'failed',
            'filename': filename,
            'error': str(e),
        }

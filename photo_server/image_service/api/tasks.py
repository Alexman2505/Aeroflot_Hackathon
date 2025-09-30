import os
import requests
from celery import shared_task
from django.utils import timezone
from django.conf import settings


@shared_task
def send_single_image(temp_file_path, token, user_data):
    """
    Фоновая задача для отправки одного изображения.
    """
    print(
        f"[Celery] send_single_image запущен: {os.path.basename(temp_file_path)}",
        flush=True,
    )
    try:
        # Читаем сохраненный файл
        with open(temp_file_path, 'rb') as f:
            image_data = f.read()
            filename = os.path.basename(temp_file_path)

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

        # Отправка на API
        response = requests.post(
            settings.AEROTOOLKIT_API_URL,
            files=files,
            data=data,
            headers=headers,
            timeout=20,
        )

        # Очищаем временный файл
        try:
            os.remove(temp_file_path)
        except OSError:
            pass
        print(
            f" [Celery] Файл отправлен: {os.path.basename(temp_file_path)}",
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
        print(f"[Celery] Ошибка: {e}", flush=True)
        # Очищаем временный файл в случае ошибки
        try:
            os.remove(temp_file_path)
        except OSError:
            pass
        return {
            'status': 'failed',
            'filename': os.path.basename(temp_file_path),
            'error': str(e),
        }


@shared_task
def process_image_batch(file_paths, token, user_data):
    print(
        f" [Celery] process_image_batch запущен, файлов: {len(file_paths)}",
        flush=True,
    )

    for i, file_path in enumerate(file_paths):
        print(
            f" [Celery] Запускаем send_single_image для файла {i+1}",
            flush=True,
        )
        send_single_image.delay(file_path, token, user_data)

    print(" [Celery] Все задачи отправлены в очередь", flush=True)
    return {"status": "started", "files_count": len(file_paths)}

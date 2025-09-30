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

        return {
            'status': (
                'success' if response.status_code in [200, 201] else 'failed'
            ),
            'filename': filename,
            'status_code': response.status_code,
        }

    except Exception as e:
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
    """
    Обрабатывает пачку изображений и возвращает результаты.
    """
    results = []

    # Запускаем задачи для каждого файла
    for file_path in file_paths:
        result = send_single_image.delay(file_path, token, user_data)
        results.append(result)

    # Ждем завершения всех задач (можно убрать для полной асинхронности)
    completed_results = []
    for result in results:
        completed_results.append(result.get(timeout=30))

    return completed_results

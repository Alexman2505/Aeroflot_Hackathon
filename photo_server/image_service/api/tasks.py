import os
import requests
from celery import shared_task
from django.utils import timezone
from django.conf import settings


@shared_task
def send_single_image(temp_file_path, token, user_data):
    """
    Фоновая задача для отправки одного изображения на основной бэкенд.

    Выполняет следующие операции:
    1. Чтение сохраненного временного файла
    2. Подготовка метаданных и текстового описания
    3. Отправка multipart/form-data запроса к API
    4. Очистка временных файлов после обработки
    5. Возврат статуса выполнения задачи

    Args:
        temp_file_path: Путь к временному файлу изображения
        token: Токен авторизации для API
        user_data: Словарь с данными пользователя (имя, настройки обработки)

    Returns:
        dict: Результат выполнения задачи со статусом и дополнительной информацией
    """
    filename = os.path.basename(temp_file_path)

    try:
        # Читаем сохраненный файл
        with open(temp_file_path, 'rb') as f:
            image_data = f.read()

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

        # Отправка на API основного бэкенда
        response = requests.post(
            settings.AEROTOOLKIT_API_URL,
            files=files,
            data=data,
            headers=headers,
            timeout=20,
        )

        # Очищаем временный файл после успешной отправки
        try:
            os.remove(temp_file_path)
        except OSError:
            # Игнорируем ошибки удаления файла
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
            'filename': filename,
            'error': str(e),
        }

import os
import requests
from celery import shared_task
from django.utils import timezone
from django.conf import settings
import time


@shared_task
def send_single_image(temp_file_path, token, user_data):
    """
    Фоновая задача для отправки одного изображения.
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
            timeout=20,
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


# Старая задача - оставляем для обратной совместимости, но не используем
@shared_task
def process_image_batch(file_paths, token, user_data):
    """
    СТАРАЯ задача для обработки пакета изображений.
    Оставляем для обратной совместимости.
    """
    print(
        f"[{time.time()}] [Celery]   process_image_batch ВЫЗВАН (устаревший метод)",
        flush=True,
    )

    # Для обратной совместимости - запускаем отдельные задачи
    for i, file_path in enumerate(file_paths):
        send_single_image.delay(file_path, token, user_data)

    return {"status": "started", "files_count": len(file_paths)}

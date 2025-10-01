from celery import shared_task
from django.core.files.base import ContentFile
import uuid
from instruments.models import Instrument
from .yolo_utils import run_yolo_inference


@shared_task
def process_instrument_with_yolo(
    instrument_id, image_data, expected_objects, expected_confidence
):
    """
    Фоновая Celery задача для обработки инструмента через YOLO модель.

    Выполняет асинхронную обработку изображения инструмента с использованием
    YOLO модели для детекции объектов. Задача запускается после создания
    инструмента и обновляет его данными распознавания.

    Процесс выполнения:
    1. Получает инструмент из базы данных по ID
    2. Выполняет YOLO инференс на переданных данных изображения
    3. Форматирует результаты детекции в читаемый текст
    4. Сохраняет аннотированное изображение с bounding boxes
    5. Обновляет запись инструмента в базе данных

    Args:
        instrument_id (int): ID инструмента в базе данных
        image_data (bytes): Бинарные данные изображения для обработки
        expected_objects (int): Ожидаемое количество объектов на изображении
        expected_confidence (float): Порог уверенности для детекции (0.0-1.0)

    Returns:
        dict: Результат выполнения задачи:
            - status (str): 'success' при успешном выполнении, 'error' при ошибке
            - instrument_id (int): ID обработанного инструмента
            - error (str): Сообщение об ошибке (только при status='error')

    Raises:
        Instrument.DoesNotExist: Если инструмент с указанным ID не найден
        Exception: Любые другие ошибки при обработке изображения

    Example:
        >>> result = process_instrument_with_yolo.delay(
        ...     instrument_id=101,
        ...     image_data=b'...',
        ...     expected_objects=11,
        ...     expected_confidence=0.8
        ... )
        >>> # Задача выполняется асинхронно в Celery worker
    """
    try:
        print(
            f" [BACKEND CELERY] Starting YOLO processing for instrument {instrument_id}",
            flush=True,
        )

        # Получаем инструмент из базы данных
        instrument = Instrument.objects.get(id=instrument_id)

        # Выполняем YOLO обработку изображения
        yolo_results, processed_image_bytes = run_yolo_inference(
            image_data,
            conf_thres=expected_confidence,
            expected_objects=expected_objects,
            expected_confidence=expected_confidence,
        )

        # Обновляем текст инструмента с результатами YOLO анализа
        original_text = instrument.text
        detections = yolo_results.get("detections", [])

        if not detections:
            yolo_section = "YOLO анализ: инструменты не обнаружены"
        else:
            # Форматируем список обнаруженных объектов
            detected_items = [
                f"{i+1}. {det['class']} (Уровень уверенности: {det['confidence']:.2f})"
                for i, det in enumerate(detections)
            ]
            yolo_section = (
                f"YOLO анализ: обнаружено {len(detections)} объектов\n"
                + "\n".join(detected_items)
            )

        # Добавляем результаты YOLO к оригинальному тексту
        if original_text.strip():
            instrument.text = f"{original_text}\n\n{yolo_section}"
        else:
            instrument.text = yolo_section

        # Сохраняем обработанное изображение с bounding boxes
        save_filename = f"instrument_{uuid.uuid4().hex[:8]}.jpg"
        instrument.image.save(
            save_filename, ContentFile(processed_image_bytes)
        )

        print(
            f" [BACKEND CELERY] YOLO processing completed for instrument {instrument_id}",
            flush=True,
        )

        return {'status': 'success', 'instrument_id': instrument_id}

    except Instrument.DoesNotExist:
        # Обработка случая когда инструмент не найден
        error_msg = f"Instrument with id {instrument_id} does not exist"
        print(
            f" [BACKEND CELERY] Error processing instrument {instrument_id}: {error_msg}",
            flush=True,
        )
        return {'status': 'error', 'error': error_msg}

    except Exception as e:
        # Обработка всех других ошибок
        print(
            f" [BACKEND CELERY] Error processing instrument {instrument_id}: {str(e)}",
            flush=True,
        )
        return {'status': 'error', 'error': str(e)}

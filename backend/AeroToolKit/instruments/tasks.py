from celery import shared_task
from django.core.files.base import ContentFile
import uuid
from .models import Instrument
from api.yolo_utils import run_yolo_inference


@shared_task
def process_instrument_with_yolo(
    instrument_id, image_data, expected_objects, expected_confidence
):
    """
    Фоновая задача для обработки инструмента через YOLO
    """
    try:
        print(
            f" [BACKEND CELERY] Starting YOLO processing for instrument {instrument_id}",
            flush=True,
        )

        # Получаем инструмент
        instrument = Instrument.objects.get(id=instrument_id)

        # YOLO обработка
        yolo_results, processed_image_bytes = run_yolo_inference(
            image_data,
            conf_thres=expected_confidence,
            expected_objects=expected_objects,
            expected_confidence=expected_confidence,
        )

        # Обновляем текст с результатами YOLO
        original_text = instrument.text
        detections = yolo_results.get("detections", [])

        if not detections:
            yolo_section = "YOLO анализ: инструменты не обнаружены"
        else:
            detected_items = [
                f"{i+1}. {det['class']} (Уровень уверенности: {det['confidence']:.2f})"
                for i, det in enumerate(detections)
            ]
            yolo_section = (
                f"YOLO анализ: обнаружено {len(detections)} объектов\n"
                + "\n".join(detected_items)
            )

        if original_text.strip():
            instrument.text = f"{original_text}\n\n{yolo_section}"
        else:
            instrument.text = yolo_section

        # Сохраняем обработанное изображение
        save_filename = f"instrument_{uuid.uuid4().hex[:8]}.jpg"
        instrument.image.save(
            save_filename, ContentFile(processed_image_bytes)
        )

        print(
            f" [BACKEND CELERY] YOLO processing completed for instrument {instrument_id}",
            flush=True,
        )
        return {'status': 'success', 'instrument_id': instrument_id}

    except Exception as e:
        print(
            f" [BACKEND CELERY] Error processing instrument {instrument_id}: {str(e)}",
            flush=True,
        )
        return {'status': 'error', 'error': str(e)}

import cv2
import io
import numpy as np
import onnxruntime as ort
import os
from PIL import Image, ImageDraw, ImageFont
import time
from django.conf import settings

# Конфигурация YOLO
YOLO_CLASSES = settings.YOLO_CLASSES

# Путь к модели YOLO
YOLO_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), 'yolo_models', 'yolo_model.onnx'
)

# Инициализация ONNX сессии
ort_session = ort.InferenceSession(
    YOLO_MODEL_PATH, providers=["CPUExecutionProvider"]
)


def letterbox(im, new_shape=(640, 640), color=(114, 114, 114)):
    """
    Изменяет размер изображения с сохранением пропорций и добавляет паддинг.

    Аналогично функции letterbox из Ultralytics, подготавливает изображение
    к нужному размеру для модели YOLO.

    Args:
        im (numpy.ndarray): Входное изображение в формате HWC
        new_shape (int/tuple): Желаемый размер (высота, ширина)
        color (tuple): Цвет паддинга в формате (R, G, B)

    Returns:
        tuple: (изображение с паддингом, коэффициент масштабирования, (паддинг_ширина, паддинг_высота))
    """
    shape = im.shape[:2]  # высота, ширина
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    # Вычисляем коэффициент масштабирования
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))
    dw, dh = (new_shape[1] - new_unpad[0]) / 2, (
        new_shape[0] - new_unpad[1]
    ) / 2

    # Создаем изображение с паддингом
    im_resized = np.zeros(
        (new_shape[0], new_shape[1], 3), dtype=im.dtype
    ) + np.array(color, dtype=im.dtype)
    im_small = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, left = int(round(dh)), int(round(dw))
    im_resized[top : top + new_unpad[1], left : left + new_unpad[0]] = im_small
    return im_resized, r, (left, top)


def xywh2xyxy(x):
    """
    Преобразует координаты из формата [x_center, y_center, width, height] в [x1, y1, x2, y2].

    Args:
        x (numpy.ndarray): Массив bounding box'ов в формате (N, 4)

    Returns:
        numpy.ndarray: Массив bounding box'ов в формате (N, 4) [x1, y1, x2, y2]
    """
    y = x.copy()
    y[:, 0] = x[:, 0] - x[:, 2] / 2  # x1 = x_center - width/2
    y[:, 1] = x[:, 1] - x[:, 3] / 2  # y1 = y_center - height/2
    y[:, 2] = x[:, 0] + x[:, 2] / 2  # x2 = x_center + width/2
    y[:, 3] = x[:, 1] + x[:, 3] / 2  # y2 = y_center + height/2
    return y


def compute_iou(box, boxes):
    """
    Вычисляет Intersection over Union (IoU) между одним bounding box и массивом bounding box'ов.

    Args:
        box (numpy.ndarray): Один bounding box в формате [x1, y1, x2, y2]
        boxes (numpy.ndarray): Массив bounding box'ов в формате (N, 4)

    Returns:
        numpy.ndarray: Массив значений IoU для каждого bounding box'а
    """
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])

    # Вычисляем площадь пересечения
    inter_w = np.maximum(0.0, x2 - x1)
    inter_h = np.maximum(0.0, y2 - y1)
    inter = inter_w * inter_h

    # Вычисляем площади bounding box'ов
    area1 = (box[2] - box[0]) * (box[3] - box[1])
    area2 = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])

    # Вычисляем объединение
    union = area1 + area2 - inter
    return inter / (
        union + 1e-6
    )  # Добавляем эпсилон для избежания деления на ноль


def nms(boxes, scores, iou_thres=0.45):
    """
    Выполняет Non-Maximum Suppression (NMS) для набора bounding box'ов.

    Удаляет дублирующиеся детекции, оставляя только самые уверенные.

    Args:
        boxes (numpy.ndarray): Массив bounding box'ов в формате (N, 4)
        scores (numpy.ndarray): Массив уверенностей для каждого bounding box'а
        iou_thres (float): Порог IoU для подавления дубликатов

    Returns:
        list: Индексы bounding box'ов, которые нужно сохранить
    """
    if boxes.shape[0] == 0:
        return []

    # Сортируем по убыванию уверенности
    idxs = scores.argsort()[::-1]
    keep = []

    while idxs.size:
        i = idxs[0]
        keep.append(i)
        if idxs.size == 1:
            break

        # Вычисляем IoU с оставшимися bounding box'ами
        ious = compute_iou(boxes[i], boxes[idxs[1:]])

        # Оставляем только те, у которых IoU меньше порога
        idxs = idxs[1:][ious < iou_thres]

    return keep


def process_yolo_output(
    output, img_shape=640, conf_thres=0.25, iou_thres=0.45
):
    """
    Обрабатывает выходные данные модели YOLO и преобразует их в детекции.

    Args:
        output: Выходные данные модели ONNX
        img_shape (int): Размер изображения, использованный для инференса
        conf_thres (float): Порог уверенности для фильтрации детекций
        iou_thres (float): Порог IoU для NMS

    Returns:
        list: Список словарей с детекциями, каждый содержит:
              - bbox: координаты [x1, y1, x2, y2]
              - score: уверенность детекции
              - class_id: идентификатор класса
    """
    out = np.array(output)

    # Обрабатываем различные форматы выходных данных
    if out.ndim == 3:
        if out.shape[1] <= out.shape[2]:
            out = out[0].transpose(1, 0)  # (N, C)
        else:
            out = out[0]  # уже в правильном формате
    else:
        out = out.squeeze()
        if out.ndim == 2 and out.shape[1] <= 20:
            out = out.transpose(1, 0)

    if out.size == 0:
        return []

    # Извлекаем bounding boxes и scores
    boxes_xywh = out[:, :4].copy()  # x_center, y_center, width, height

    # scores для каждого класса
    scores_all = out[:, 4:]

    # Определяем классы и их уверенности
    class_ids = np.argmax(scores_all, axis=1)

    # Округляем до 3го знака после запятой
    class_scores = np.round(
        scores_all[np.arange(scores_all.shape[0]), class_ids], 3
    )

    # Добавляем эпсилон-поправку 0,001 на наше округление
    epsilon = 1e-3
    effective_threshold = conf_thres - epsilon

    # Фильтруем по порогу уверенности с поправкой
    mask = class_scores >= effective_threshold

    if not mask.any():
        return []

    boxes_xywh = boxes_xywh[mask]
    class_scores = class_scores[mask]
    class_ids = class_ids[mask]

    # Конвертируем в формат xyxy
    boxes_xyxy = xywh2xyxy(boxes_xywh)

    # Масштабируем если координаты нормализованы
    max_coord = boxes_xyxy.max()
    if max_coord <= 1.0:
        boxes_xyxy = boxes_xyxy * img_shape

    # Выполняем NMS для каждого класса отдельно
    final = []
    unique_classes = np.unique(class_ids)

    total_before_nms = 0
    total_after_nms = 0

    for c in unique_classes:
        idxs = np.where(class_ids == c)[0]
        b = boxes_xyxy[idxs]
        s = class_scores[idxs]

        class_count_before = len(b)
        total_before_nms += class_count_before

        keep = nms(b, s, iou_thres=iou_thres)

        class_count_after = len(keep)
        total_after_nms += class_count_after

        for k in keep:
            final.append(
                {
                    "bbox": b[k].tolist(),
                    "score": float(s[k]),
                    "class_id": int(c),
                }
            )

    return final


def run_yolo_inference(
    image_data,
    imgsz=640,
    conf_thres=0.7,
    iou_thres=0.7,
    expected_objects=None,
    expected_confidence=None,
):
    """
    Выполняет инференс YOLO на данных изображения и возвращает результаты с аннотированным изображением.

    Args:
        image_data (bytes): Байтовые данные изображения
        imgsz (int): Размер изображения для модели
        conf_thres (float): Порог уверенности для детекций
        iou_thres (float): Порог IoU для NMS
        expected_objects (int): Ожидаемое количество объектов (для логирования)
        expected_confidence (float): Ожидаемая уверенность (переопределяет conf_thres)

    Returns:
        tuple: (результаты детекции, байты аннотированного изображения)
    """
    # Используем переданную ожидаемую уверенность если предоставлена
    if expected_confidence is not None:
        conf_thres = float(expected_confidence)

    start = time.time()

    # Загружаем изображение
    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    orig_w, orig_h = image.size
    img_np = np.array(image)

    # Предобработка изображения
    img_pad, ratio, (pad_w, pad_h) = letterbox(
        img_np, new_shape=(imgsz, imgsz)
    )
    img_input = img_pad[:, :, ::-1].transpose(2, 0, 1)  # RGB->BGR->CHW
    img_input = np.expand_dims(img_input, axis=0).astype(np.float32) / 255.0

    # Выполняем инференс
    ort_inputs = {ort_session.get_inputs()[0].name: img_input}
    outputs = ort_session.run(None, ort_inputs)

    # Обрабатываем выходные данные
    detections_raw = process_yolo_output(
        outputs[0], img_shape=imgsz, conf_thres=conf_thres, iou_thres=iou_thres
    )

    # Конвертируем bounding boxes в координаты исходного изображения и рисуем их
    detections = []
    draw = ImageDraw.Draw(image)

    try:
        # Пробуем загрузить шрифт большого размера
        font = ImageFont.truetype(
            "arial.ttf", 50
        )  # 50 пикселей - примерно в 5 раз больше
    except:
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 50)
        except:
            # Если системные шрифты недоступны, оставляем default
            font = ImageFont.load_default()

    for det in detections_raw:
        x1, y1, x2, y2 = det["bbox"]

        # Убираем паддинг и масштабируем к исходному размеру
        x1 = (x1 - pad_w) / ratio
        x2 = (x2 - pad_w) / ratio
        y1 = (y1 - pad_h) / ratio
        y2 = (y2 - pad_h) / ratio

        # Обрезаем координаты до границ изображения
        x1 = max(0, min(orig_w, int(round(x1))))
        x2 = max(0, min(orig_w, int(round(x2))))
        y1 = max(0, min(orig_h, int(round(y1))))
        y2 = max(0, min(orig_h, int(round(y2))))

        class_id = det["class_id"]
        cls_name = (
            YOLO_CLASSES[class_id]
            if class_id < len(YOLO_CLASSES)
            else str(class_id)
        )
        score = float(det["score"])

        detections.append({"class": cls_name, "confidence": score})

        # Рисуем bounding box и подпись
        draw.rectangle([x1, y1, x2, y2], outline="green", width=10)
        label = f"{cls_name} {score:.2f}"
        text_pos = (x1, max(0, y1 - 50))
        draw.text(text_pos, label, fill="green", font=font)

    # Вычисляем время обработки
    processing_time = round(time.time() - start, 2)
    result_dict = {
        "detections": detections,
        "processing_time": processing_time,
        "status": "processed" if detections else "no_detections",
    }

    # Сохраняем аннотированное изображение
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    processed_image_bytes = buf.getvalue()

    return result_dict, processed_image_bytes

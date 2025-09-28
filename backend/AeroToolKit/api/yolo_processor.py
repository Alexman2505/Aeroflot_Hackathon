import cv2
import numpy as np
import onnxruntime as ort
import time
from PIL import Image, ImageDraw
import io


class YOLOProcessor:
    def __init__(self, model_path):
        self.session = ort.InferenceSession(model_path)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        self.class_names = [
            '1_screwdriver_minus',  # Отвертка «-»
            '2_screwdriver_plus',  # Отвертка «+»
            '3_screwdriver_torq',  # Отвертка на смещенный крест
            '4_brace',  # Коловорот
            '5_locking_pliers',  # Пассатижи контровочные
            '6_pliers',  # Пассатижи
            '7_adjustable_pliers',  # Шэрница
            '8_adjustable_wrench',  # Разводной ключ
            '9_can_opener',  # Открывашка для банок с маслом
            '10_open_end_wrench',  # Ключ рожковый накидной ¾
            '11_sidecutter',  # Бокорезы
        ]

    # def _get_class_names_from_model(self):
    #     """Извлекает имена классов из метаданных ONNX модели"""
    #     try:
    #         # Пытаемся получить классы из метаданных модели
    #         model_metadata = self.session.get_modelmeta()
    #         custom_metadata = model_metadata.custom_metadata_map

    #         # YOLOv8 обычно хранит классы в metadata
    #         if 'names' in custom_metadata:
    #             import json

    #             names_json = custom_metadata['names']
    #             names_dict = json.loads(names_json)
    #             return [names_dict[str(i)] for i in range(len(names_dict))]

    #         # Альтернативный способ - через labels
    #         elif 'labels' in custom_metadata:
    #             labels_str = custom_metadata['labels']
    #             return labels_str.split(',')

    #     except Exception as e:
    #         print(f"Could not extract class names from model: {e}")

    def preprocess(self, image_data):
        """Препроцессинг изображения для YOLO"""
        image = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Ресайз до 640x640 (как при обучении)
        resized = cv2.resize(image, (640, 640))

        # Нормализация и преобразование формата
        input_tensor = resized / 255.0
        input_tensor = input_tensor.transpose(2, 0, 1)
        input_tensor = np.expand_dims(input_tensor, axis=0).astype(np.float32)

        return input_tensor, image.shape[1], image.shape[0], image

    def postprocess(
        self, outputs, orig_width, orig_height, conf_threshold=0.25
    ):
        """Постпроцессинг выхода YOLO"""
        detections = []
        predictions = outputs[0][0]  # [num_detections, 6]

        for detection in predictions:
            if len(detection) < 6:
                continue

            x_center, y_center, width, height, confidence, class_id = detection

            if confidence > conf_threshold:
                # Масштабируем к оригинальным размерам
                scale_x, scale_y = orig_width / 640, orig_height / 640

                x_center *= scale_x
                y_center *= scale_y
                width *= scale_x
                height *= scale_y

                # Конвертируем в bbox координаты
                x_min = max(0, int(x_center - width / 2))
                y_min = max(0, int(y_center - height / 2))
                x_max = min(orig_width, int(x_center + width / 2))
                y_max = min(orig_height, int(y_center + height / 2))

                class_id = int(class_id)
                class_name = (
                    self.class_names[class_id]
                    if class_id < len(self.class_names)
                    else f"class_{class_id}"
                )

                detections.append(
                    {
                        'class': class_name,
                        'confidence': float(confidence),
                        'bbox': [x_min, y_min, x_max, y_max],
                    }
                )

        return detections

    def draw_boxes(self, image, detections):
        """Рисует bounding boxes на изображении"""
        pil_image = Image.fromarray(image)
        draw = ImageDraw.Draw(pil_image)

        for detection in detections:
            x_min, y_min, x_max, y_max = detection['bbox']

            # Рисуем bounding box
            draw.rectangle(
                [x_min, y_min, x_max, y_max], outline="red", width=3
            )

            # Текст с классом и уверенностью
            label = f"{detection['class']}: {detection['confidence']:.2f}"
            draw.text((x_min, y_min), label, fill="red")

        return pil_image

    def process(self, image_data):
        """Основной метод обработки"""
        start_time = time.time()

        try:
            # Препроцессинг
            input_tensor, orig_width, orig_height, orig_image = (
                self.preprocess(image_data)
            )

            # Инференс
            outputs = self.session.run(
                [self.output_name], {self.input_name: input_tensor}
            )

            # Постпроцессинг
            detections = self.postprocess(outputs, orig_width, orig_height)

            # Рисуем боксы
            annotated_image = self.draw_boxes(orig_image, detections)

            # Конвертируем в bytes
            img_byte_arr = io.BytesIO()
            annotated_image.save(img_byte_arr, format='JPEG')

            return {
                'detections': detections,
                'processing_time': time.time() - start_time,
                'status': 'processed',
                'annotated_image': img_byte_arr.getvalue(),
            }

        except Exception as e:
            return {
                'detections': [],
                'processing_time': time.time() - start_time,
                'status': f'error: {str(e)}',
                'annotated_image': None,
            }


# Глобальный инстанс
yolo_processor = None


def init_yolo(model_path):
    global yolo_processor
    yolo_processor = YOLOProcessor(model_path)


def get_yolo():
    return yolo_processor

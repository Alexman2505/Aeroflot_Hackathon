import base64
import uuid
from rest_framework import serializers
from django.core.files.base import ContentFile
from instruments.models import Instrument
from .yolo_utils import run_yolo_inference
from django.conf import settings


class InstrumentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения и отображения инструментов.

    Предоставляет полную информацию об инструменте включая URL изображения
    и имя сотрудника в читаемом формате.
    """

    employee_username = serializers.CharField(
        source='employee.username', read_only=True
    )
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Instrument
        fields = [
            'id',
            'text',
            'pub_date',
            'employee',
            'employee_username',
            'image',
            'image_url',
            'expected_objects',
            'filename',
        ]
        read_only_fields = ['employee', 'pub_date']

    def get_image_url(self, obj):
        """
        Генерирует полный URL для изображения инструмента.

        Args:
            obj: Объект Instrument

        Returns:
            str: Абсолютный URL изображения или None если изображение отсутствует
        """
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class InstrumentCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания инструментов с обработкой изображений через YOLO.

    Обрабатывает base64 изображения, выполняет детекцию объектов через YOLO модель
    и сохраняет аннотированное изображение вместе с результатами анализа.
    """

    full_base64_string = serializers.CharField(write_only=True, required=True)
    image = serializers.ImageField(read_only=True)
    filename = serializers.CharField(write_only=True, required=False)
    expected_objects = serializers.IntegerField(
        write_only=True, required=False
    )
    expected_confidence = serializers.FloatField(
        write_only=True, required=False
    )

    class Meta:
        model = Instrument
        fields = [
            'id',
            'text',
            'pub_date',
            'employee',
            'image',
            'full_base64_string',
            'filename',
            'expected_objects',
            'expected_confidence',
        ]
        read_only_fields = ['employee', 'pub_date', 'image']

    def validate(self, attrs):
        """
        Валидирует данные перед созданием инструмента.
        """
        errors = {}

        # Проверка текста
        text = attrs.get('text', '').strip()
        if not text:
            errors['text'] = 'Текст обязателен'

        # Проверка base64 строки
        full_base64_string = attrs.get('full_base64_string', '')
        if not full_base64_string:
            errors['full_base64_string'] = (
                'Изображение в формате base64 обязательно'
            )
        elif not full_base64_string.startswith('data:image/'):
            errors['full_base64_string'] = 'Неверный формат base64'

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        """
        Создает новый инструмент с обработкой изображения через YOLO.
        """
        try:
            # Извлекаем поля, которые не являются полями модели
            full_base64_string = validated_data.pop("full_base64_string")

            # Извлекаем дополнительные параметры
            filename = validated_data.pop("filename", None)
            expected_objects = validated_data.pop("expected_objects", None)
            expected_confidence = validated_data.pop(
                "expected_confidence", settings.EXPECTED_CONFIDENCE
            )

            # Декодируем base64 изображение
            base64_data = full_base64_string.split(",", 1)[1]

            try:
                image_data = base64.b64decode(base64_data)
            except Exception as e:
                raise serializers.ValidationError(
                    {"full_base64_string": f"Ошибка base64: {str(e)}"}
                )

            # Устанавливаем текущего пользователя как сотрудника
            request = self.context.get("request")
            if request and request.user.is_authenticated:
                validated_data["employee"] = request.user
            else:
                raise serializers.ValidationError(
                    {"employee": "Пользователь не аутентифицирован"}
                )

            # Выполняем YOLO инференс с переданными параметрами
            try:
                yolo_results, processed_image_bytes = run_yolo_inference(
                    image_data,
                    expected_objects=expected_objects,
                    expected_confidence=expected_confidence,
                )
            except Exception as e:
                raise serializers.ValidationError(
                    {"image": f"Ошибка обработки изображения: {str(e)}"}
                )

            # Формируем итоговый текст с информацией о файле и результатами YOLO
            original_text = validated_data.get("text", "")

            # Добавляем информацию о файле и ожиданиях
            file_info = []
            if filename:
                file_info.append(f"Исходное имя файла: {filename}")
            if expected_objects:
                file_info.append(
                    f"Ожидаемое количество объектов: {expected_objects}"
                )
            if expected_confidence:
                file_info.append(
                    f"Ожидаемая уверенность распознавания: {expected_confidence}"
                )

            if file_info:
                original_text += "\n\n" + "\n".join(file_info)

            # Добавляем результаты YOLO анализа
            validated_data["text"] = self.add_yolo_results_to_text(
                original_text, yolo_results
            )

            # Создаем имя файла для сохранения изображения
            image_format = full_base64_string.split(";")[0].split("/")[1]
            save_filename = f"instrument_{uuid.uuid4().hex[:8]}.{image_format}"

            # Создаем и сохраняем инструмент
            instrument = Instrument(**validated_data)

            # Сохраняем дополнительные поля модели
            instrument.filename = filename
            instrument.expected_objects = expected_objects or 11

            # Сохраняем изображение
            instrument.image.save(
                save_filename, ContentFile(processed_image_bytes)
            )

            return instrument

        except Exception as e:
            raise

    def add_yolo_results_to_text(self, original_text, yolo_results):
        """
        Форматирует результаты YOLO анализа для добавления в текст инструмента.
        """
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

        # Объединяем исходный текст с результатами YOLO
        if original_text.strip():
            result = f"{original_text}\n\n{yolo_section}"
        else:
            result = yolo_section

        return result

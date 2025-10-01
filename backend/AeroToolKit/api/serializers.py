import uuid
import time
from rest_framework import serializers
from django.core.files.base import ContentFile
from instruments.models import Instrument
from .tasks import process_instrument_with_yolo


class InstrumentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения и отображения инструментов.
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
            'expected_confidence',
            'filename',
        ]
        read_only_fields = ['employee', 'pub_date']

    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class InstrumentCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания инструментов с обработкой изображений через YOLO.
    Теперь принимает бинарные файлы вместо base64.
    """

    image = serializers.ImageField(
        write_only=True, required=True, help_text="Бинарный файл изображения"
    )
    filename = serializers.CharField(write_only=True, required=False)
    expected_objects = serializers.IntegerField(write_only=True, required=True)
    expected_confidence = serializers.FloatField(
        write_only=True, required=True
    )

    class Meta:
        model = Instrument
        fields = [
            'id',
            'text',
            'pub_date',
            'employee',
            'image',  # Теперь write_only для приема файлов
            'filename',
            'expected_objects',
            'expected_confidence',
        ]
        read_only_fields = ['employee', 'pub_date']

    def validate(self, attrs):
        """
        Валидирует данные перед созданием инструмента.
        """
        print(
            f" [BACKEND VALIDATE] Validation START at {time.time()}",
            flush=True,
        )
        validation_start = time.time()

        errors = {}

        # Проверка текста
        text = attrs.get('text', '').strip()
        if not text:
            errors['text'] = 'Текст обязателен'

        # Проверка изображения
        image = attrs.get('image')
        if not image:
            errors['image'] = 'Изображение обязательно'
        elif not hasattr(
            image, 'content_type'
        ) or not image.content_type.startswith('image/'):
            errors['image'] = 'Файл должен быть изображением'

        # Проверка expected_objects
        expected_objects = attrs.get('expected_objects')
        if expected_objects is None:
            errors['expected_objects'] = (
                'Ожидаемое количество объектов обязательно'
            )
        elif expected_objects <= 0:
            errors['expected_objects'] = (
                'Количество объектов должно быть положительным числом'
            )

        # Проверка expected_confidence
        expected_confidence = attrs.get('expected_confidence')
        if expected_confidence is None:
            errors['expected_confidence'] = (
                'Ожидаемая уверенность распознавания обязательна'
            )
        elif not (0 < expected_confidence <= 1):
            errors['expected_confidence'] = (
                'Уверенность распознавания должна быть между 0 и 1'
            )

        if errors:
            validation_time = time.time() - validation_start
            print(
                f" [BACKEND VALIDATE] Validation FAILED: {validation_time:.3f}s",
                flush=True,
            )
            raise serializers.ValidationError(errors)

        validation_time = time.time() - validation_start
        print(
            f" [BACKEND VALIDATE] Validation PASSED: {validation_time:.3f}s",
            flush=True,
        )
        return attrs

    def create(self, validated_data):
        """
        Создает новый инструмент с обработкой изображения через YOLO.
        Теперь работает с бинарным файлом вместо base64.
        """
        print(
            f" [BACKEND CREATE] Fast creation START at {time.time()}",
            flush=True,
        )
        start_time = time.time()

        try:
            # Извлекаем данные
            image_file = validated_data.pop("image")
            filename = validated_data.pop("filename", None)
            expected_objects = validated_data.pop("expected_objects", None)
            expected_confidence = validated_data.pop("expected_confidence")

            # Устанавливаем пользователя
            request = self.context.get("request")
            if request and request.user.is_authenticated:
                validated_data["employee"] = request.user

            # БЫСТРОЕ сохранение без YOLO
            instrument = Instrument(**validated_data)
            instrument.filename = filename or image_file.name
            instrument.expected_objects = expected_objects or 11

            # Сохраняем оригинальное изображение
            instrument.image.save(
                f"temp_{uuid.uuid4().hex[:8]}.jpg", image_file
            )
            instrument.save()

            # ЗАПУСКАЕМ YOLO В ФОНОВОМ РЕЖИМЕ
            image_data = image_file.read()

            process_instrument_with_yolo.delay(
                instrument.id,
                image_data,
                expected_objects or 11,
                expected_confidence,
            )

            total_time = time.time() - start_time
            print(
                f" [BACKEND CREATE] FAST creation completed: {total_time:.3f}s",
                flush=True,
            )
            print(
                f" [BACKEND CREATE] YOLO processing started in background for instrument {instrument.id}",
                flush=True,
            )

            return instrument

        except Exception as e:
            error_time = time.time() - start_time
            print(
                f" [BACKEND CREATE] Error after {error_time:.3f}s: {str(e)}",
                flush=True,
            )
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

        if original_text.strip():
            result = f"{original_text}\n\n{yolo_section}"
        else:
            result = yolo_section

        return result

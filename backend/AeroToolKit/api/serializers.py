import base64
import uuid
import os
from rest_framework import serializers
from django.core.files.base import ContentFile
from instruments.models import Instrument

# Импортируем YOLO процессор
from .yolo_processor import init_yolo, get_yolo


class InstrumentSerializer(serializers.ModelSerializer):
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
    full_base64_string = serializers.CharField(write_only=True, required=True)
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Instrument
        fields = [
            'id',
            'text',
            'pub_date',
            'employee',
            'image',
            'full_base64_string',
        ]
        read_only_fields = ['employee', 'pub_date', 'image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Инициализируем YOLO один раз
        try:
            model_path = os.path.join(
                os.path.dirname(__file__), 'yolo_models', 'yolo_model.onnx'
            )
            init_yolo(model_path)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize YOLO model: {e}")

    def validate(self, attrs):
        errors = {}

        if not attrs.get('text', '').strip():
            errors['text'] = 'Текст обязателен'

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
        # Извлекаем и декодируем base64
        full_base64_string = validated_data.pop('full_base64_string')
        base64_data = full_base64_string.split(',', 1)[1]
        image_data = base64.b64decode(base64_data)

        # Получаем пользователя
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['employee'] = request.user
        else:
            raise serializers.ValidationError(
                {'employee': 'Пользователь не аутентифицирован'}
            )

        # Обрабатываем YOLO
        yolo_processor = get_yolo()
        yolo_results = yolo_processor.process(image_data)

        # Используем аннотированное изображение
        image_data = yolo_results['annotated_image']

        # Обновляем текст с результатами
        original_text = validated_data.get('text', '')
        validated_data['text'] = self._add_yolo_results(
            original_text, yolo_results
        )

        # Сохраняем инструмент
        filename = f"instrument_{uuid.uuid4().hex[:8]}.jpg"
        instrument = Instrument(**validated_data)
        instrument.image.save(filename, ContentFile(image_data))

        return instrument

    def _add_yolo_results(self, original_text, yolo_results):
        detections = yolo_results.get('detections', [])

        if not detections:
            yolo_section = "YOLO анализ: инструменты не обнаружены"
        else:
            detected_items = [
                f"{i}. {d['class']} (точность: {d['confidence']:.2f})"
                for i, d in enumerate(detections, 1)
            ]
            yolo_section = (
                f"Обнаружено {len(detections)} объектов:\n"
                + "\n".join(detected_items)
            )

        return (
            f"{original_text}\n\n{yolo_section}"
            if original_text.strip()
            else yolo_section
        )

import base64
import uuid
from rest_framework import serializers
from django.core.files.base import ContentFile
from instruments.models import Instrument


class InstrumentSerializer(serializers.ModelSerializer):
    '''Сериализатор для чтения, обновления, удаления'''

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
    '''Сериализатор ТОЛЬКО для создания с обязательным base64 и YOLO'''

    full_base64_string = serializers.CharField(
        write_only=True,
        required=True,
        help_text="Обязательное поле: изображение в формате base64 (data:image/...)",
    )
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

    def validate(self, attrs):
        """Валидация обязательных полей"""
        errors = {}

        if not attrs.get('text', '').strip():
            errors['text'] = 'Текст обязателен'

        full_base64_string = attrs.get('full_base64_string', '')
        if not full_base64_string:
            errors['full_base64_string'] = (
                'Изображение в формате base64 обязательно'
            )
        elif not full_base64_string.startswith('data:image/'):
            errors['full_base64_string'] = (
                'Неверный формат. Ожидается: data:image/<format>;base64,<data>'
            )

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        """ВСЯ логика создания: base64 - YOLO - сохранение"""
        # 1. Извлекаем base64
        full_base64_string = validated_data.pop('full_base64_string')
        base64_data = full_base64_string.split(',', 1)[1]

        # 2. Декодируем base64
        try:
            image_data = base64.b64decode(base64_data)
        except Exception as e:
            raise serializers.ValidationError(
                {
                    'full_base64_string': f'Ошибка декодирования base64: {str(e)}'
                }
            )

        # 3. Получаем пользователя из контекста
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['employee'] = request.user
        else:
            raise serializers.ValidationError(
                {'employee': 'Пользователь не аутентифицирован'}
            )

        # 4. Обрабатываем YOLO (заглушка)
        yolo_results = self.yolo_processing_stub(image_data)

        # 5. Обновляем текст с результатами YOLO
        original_text = validated_data.get('text', '')
        validated_data['text'] = self.add_yolo_results_to_text(
            original_text, yolo_results
        )

        # 6. Создаем имя файла
        image_format = full_base64_string.split(';')[0].split('/')[1]
        filename = f"instrument_{uuid.uuid4().hex[:8]}.{image_format}"

        # 7. Создаем и сохраняем инструмент
        instrument = Instrument(**validated_data)
        instrument.image.save(filename, ContentFile(image_data))

        return instrument

    def yolo_processing_stub(self, image_data):
        """ЗАГЛУШКА для YOLO обработки"""
        # Временная заглушка - возвращаем фиктивные результаты
        return {
            'detections': [
                {'class': 'screwdriver', 'confidence': 0.85},
                {'class': 'hammer', 'confidence': 0.92},
                {'class': 'wrench', 'confidence': 0.78},
            ],
            'processing_time': 0.45,
            'status': 'processed',
        }

    def add_yolo_results_to_text(self, original_text, yolo_results):
        """Добавляем результаты YOLO к тексту"""
        detections = yolo_results.get('detections', [])

        if not detections:
            yolo_section = "YOLO анализ: инструменты не обнаружены"
        else:
            detected_items = []
            for i, detection in enumerate(detections, 1):
                detected_items.append(
                    f"{i}. {detection['class']} (точность: {detection['confidence']:.2f})"
                )

            yolo_section = (
                f"YOLO анализ: обнаружено {len(detections)} объектов\n"
                + "\n".join(detected_items)
            )

        # Объединяем оригинальный текст с результатами YOLO
        if original_text.strip():
            return f"{original_text}\n\n{yolo_section}"
        else:
            return yolo_section

import uuid
from rest_framework import serializers
from django.core.files.base import ContentFile
from instruments.models import Instrument
from .yolo_utils import run_yolo_inference


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
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        """
        Создает новый инструмент с обработкой изображения через YOLO.
        Теперь работает с бинарным файлом вместо base64.
        """
        try:
            # Извлекаем бинарный файл изображения
            image_file = validated_data.pop("image")

            # Извлекаем дополнительные параметры
            filename = validated_data.pop("filename", None)
            expected_objects = validated_data.pop("expected_objects", None)
            expected_confidence = validated_data.pop("expected_confidence")

            # Читаем данные изображения
            image_data = image_file.read()

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
                    conf_thres=expected_confidence,
                    expected_objects=expected_objects,
                    expected_confidence=expected_confidence,
                )
            except Exception as e:
                raise serializers.ValidationError(
                    {"image": f"Ошибка обработки изображения: {str(e)}"}
                )

            # Формируем итоговый текст с информацией о файле и результатами YOLO
            original_text = validated_data.get("text", "")
            validated_data["text"] = self.add_yolo_results_to_text(
                original_text, yolo_results
            )

            # Создаем имя файла для сохранения изображения
            original_name = image_file.name
            image_format = (
                original_name.split('.')[-1] if '.' in original_name else 'jpg'
            )
            save_filename = f"instrument_{uuid.uuid4().hex[:8]}.{image_format}"

            # Создаем и сохраняем инструмент
            instrument = Instrument(**validated_data)

            # Сохраняем дополнительные поля модели
            instrument.filename = filename or original_name
            instrument.expected_objects = expected_objects or 11

            # Сохраняем обработанное изображение
            instrument.image.save(
                save_filename, ContentFile(processed_image_bytes)
            )

            return instrument

        except Exception as e:
            print(f"Ошибка создания инструмента: {str(e)}")
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

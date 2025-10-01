import uuid
import time
from rest_framework import serializers
from django.core.files.base import ContentFile
from instruments.models import Instrument
from .tasks import process_instrument_with_yolo


class InstrumentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения и отображения инструментов.

    Предоставляет сериализованное представление инструментов для операций чтения.
    Включает дополнительные вычисляемые поля для удобства отображения.

    Attributes:
        employee_username (str): Имя пользователя, связанного с инструментом
        image_url (str): Полный URL изображения инструмента
    """

    employee_username = serializers.CharField(
        source='employee.username',
        read_only=True,
        help_text="Имя пользователя, создавшего инструмент",
    )
    image_url = serializers.SerializerMethodField(
        help_text="Полный URL для доступа к изображению инструмента"
    )

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
        """
        Генерирует полный URL для изображения инструмента.

        Args:
            obj (Instrument): Объект инструмента

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

    Обрабатывает создание новых инструментов с загрузкой бинарных файлов изображений
    и последующей асинхронной обработкой через YOLO модель для детекции объектов.

    Особенности:
        - Принимает бинарные файлы вместо base64
        - Выполняет валидацию входных данных
        - Сохраняет инструмент в базу данных
        - Запускает асинхронную YOLO обработку через Celery
        - Использует временные файлы для избежания блокировок

    Attributes:
        image (ImageField): Бинарный файл изображения (обязательный)
        filename (str): Исходное имя файла (опционально)
        expected_objects (int): Ожидаемое количество объектов (обязательный)
        expected_confidence (float): Ожидаемая уверенность распознавания (обязательный)
    """

    image = serializers.ImageField(
        write_only=True,
        required=True,
        help_text="Бинарный файл изображения для обработки",
    )
    filename = serializers.CharField(
        write_only=True,
        required=False,
        help_text="Исходное имя файла изображения",
    )
    expected_objects = serializers.IntegerField(
        write_only=True,
        required=True,
        help_text="Ожидаемое количество объектов на изображении",
    )
    expected_confidence = serializers.FloatField(
        write_only=True,
        required=True,
        help_text="Порог уверенности для детекции объектов (0.0 - 1.0)",
    )

    class Meta:
        model = Instrument
        fields = [
            'id',
            'text',
            'pub_date',
            'employee',
            'image',
            'filename',
            'expected_objects',
            'expected_confidence',
        ]
        read_only_fields = ['employee', 'pub_date']

    def validate(self, attrs):
        """
        Валидирует данные перед созданием инструмента.

        Выполняет комплексную проверку всех обязательных полей и их корректности:
        - Проверяет наличие и корректность текстового описания
        - Валидирует файл изображения (формат, тип)
        - Проверяет ожидаемое количество объектов
        - Валидирует порог уверенности распознавания

        Args:
            attrs (dict): Словарь с данными для валидации

        Returns:
            dict: Валидированные данные

        Raises:
            ValidationError: Если данные не проходят валидацию
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

        Процесс создания:
        1. Извлекает и валидирует данные из запроса
        2. Создает объект инструмента с базовой информацией
        3. Сохраняет оригинальное изображение в базу данных
        4. Перематывает файл для повторного чтения
        5. Запускает асинхронную YOLO обработку через Celery

        Args:
            validated_data (dict): Валидированные данные для создания инструмента

        Returns:
            Instrument: Созданный объект инструмента

        Raises:
            Exception: В случае ошибок при создании инструмента
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

            # Устанавливаем пользователя из контекста запроса
            request = self.context.get("request")
            if request and request.user.is_authenticated:
                validated_data["employee"] = request.user

            # БЫСТРОЕ сохранение без YOLO - создаем базовую запись
            instrument = Instrument(**validated_data)
            instrument.filename = filename or image_file.name
            instrument.expected_objects = expected_objects or 11

            # Сохраняем оригинальное изображение во временный файл
            instrument.image.save(
                f"temp_{uuid.uuid4().hex[:8]}.jpg", image_file
            )
            instrument.save()

            # КРИТИЧЕСКИ ВАЖНО: перематываем файл для повторного чтения
            image_file.seek(0)

            # ЗАПУСКАЕМ YOLO В ФОНОВОМ РЕЖИМЕ через Celery
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

        Преобразует результаты детекции объектов в читабельный формат
        и добавляет их к оригинальному тексту инструмента.

        Args:
            original_text (str): Исходный текст инструмента
            yolo_results (dict): Результаты YOLO обработки с детекциями

        Returns:
            str: Текст инструмента с добавленными результатами YOLO анализа
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

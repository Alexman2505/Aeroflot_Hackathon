import uuid
import time
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
            f" [BACKEND CREATE] Serializer create START at {time.time()}",
            flush=True,
        )
        start_time = time.time()

        try:
            # Логируем полученные данные
            print(
                f" [BACKEND CREATE] Validated data keys: {list(validated_data.keys())}",
                flush=True,
            )

            # Извлекаем бинарный файл изображения
            image_file = validated_data.pop("image")
            print(
                f" [BACKEND CREATE] Image file: {image_file.name}, {image_file.size} bytes",
                flush=True,
            )

            # Извлекаем дополнительные параметры
            filename = validated_data.pop("filename", None)
            expected_objects = validated_data.pop("expected_objects", None)
            expected_confidence = validated_data.pop("expected_confidence")
            print(
                f" [BACKEND CREATE] Params - expected_objects: {expected_objects}, expected_confidence: {expected_confidence}",
                flush=True,
            )

            # Читаем данные изображения
            read_start = time.time()
            print(
                f" [BACKEND CREATE] Reading image data at {read_start}",
                flush=True,
            )
            image_data = image_file.read()
            read_time = time.time() - read_start
            print(
                f" [BACKEND CREATE] Image read completed: {read_time:.3f}s, Size: {len(image_data)} bytes",
                flush=True,
            )

            # Устанавливаем текущего пользователя как сотрудника
            user_start = time.time()
            print(
                f"👤 [BACKEND CREATE] Setting user at {user_start}", flush=True
            )
            request = self.context.get("request")
            if request and request.user.is_authenticated:
                validated_data["employee"] = request.user
                print(
                    f" [BACKEND CREATE] User set: {request.user.username}",
                    flush=True,
                )
            else:
                raise serializers.ValidationError(
                    {"employee": "Пользователь не аутентифицирован"}
                )
            user_time = time.time() - user_start
            print(
                f" [BACKEND CREATE] User setup: {user_time:.3f}s", flush=True
            )

            # YOLO обработка
            yolo_start = time.time()
            print(
                f" [BACKEND CREATE] Starting YOLO inference at {yolo_start}",
                flush=True,
            )

            try:
                yolo_results, processed_image_bytes = run_yolo_inference(
                    image_data,
                    conf_thres=expected_confidence,
                    expected_objects=expected_objects,
                    expected_confidence=expected_confidence,
                )
                yolo_duration = time.time() - yolo_start
                print(
                    f" [BACKEND CREATE] YOLO completed: {yolo_duration:.3f}s",
                    flush=True,
                )
                print(
                    f" [BACKEND CREATE] YOLO detected {len(yolo_results.get('detections', []))} objects",
                    flush=True,
                )
            except Exception as e:
                yolo_duration = time.time() - yolo_start
                print(
                    f" [BACKEND CREATE] YOLO ERROR after {yolo_duration:.3f}s: {str(e)}",
                    flush=True,
                )
                raise serializers.ValidationError(
                    {"image": f"Ошибка обработки изображения: {str(e)}"}
                )

            # Формируем итоговый текст
            text_start = time.time()
            print(
                f" [BACKEND CREATE] Formatting text at {text_start}",
                flush=True,
            )
            original_text = validated_data.get("text", "")
            validated_data["text"] = self.add_yolo_results_to_text(
                original_text, yolo_results
            )
            text_time = time.time() - text_start
            print(
                f"[BACKEND CREATE] Text formatting: {text_time:.3f}s",
                flush=True,
            )

            # Создаем имя файла для сохранения изображения
            filename_start = time.time()
            print(
                f" [BACKEND CREATE] Creating filename at {filename_start}",
                flush=True,
            )
            original_name = image_file.name
            image_format = (
                original_name.split('.')[-1] if '.' in original_name else 'jpg'
            )
            save_filename = f"instrument_{uuid.uuid4().hex[:8]}.{image_format}"
            filename_time = time.time() - filename_start
            print(
                f" [BACKEND CREATE] Filename creation: {filename_time:.3f}s",
                flush=True,
            )

            # Создаем и сохраняем инструмент
            create_start = time.time()
            print(
                f" [BACKEND CREATE] Creating instrument object at {create_start}",
                flush=True,
            )
            instrument = Instrument(**validated_data)

            # Сохраняем дополнительные поля модели
            instrument.filename = filename or original_name
            instrument.expected_objects = expected_objects or 11
            create_time = time.time() - create_start
            print(
                f" [BACKEND CREATE] Object creation: {create_time:.3f}s",
                flush=True,
            )

            # Сохраняем обработанное изображение
            save_start = time.time()
            print(
                f" [BACKEND CREATE] Saving image to storage at {save_start}",
                flush=True,
            )
            instrument.image.save(
                save_filename, ContentFile(processed_image_bytes)
            )
            save_time = time.time() - save_start
            print(
                f" [BACKEND CREATE] Image save completed: {save_time:.3f}s",
                flush=True,
            )

            total_time = time.time() - start_time
            print(
                f"🏁 [BACKEND CREATE] TOTAL PROCESSING COMPLETE: {total_time:.3f}s",
                flush=True,
            )
            print(
                f" [BACKEND CREATE] Instrument created successfully! ID: {instrument.id}",
                flush=True,
            )

            return instrument

        except Exception as e:
            error_time = time.time()
            total_time = error_time - start_time
            print(
                f" [BACKEND CREATE] ERROR after {total_time:.3f}s: {str(e)}",
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

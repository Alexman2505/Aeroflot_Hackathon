from django import forms
from .models import Instrument


class InstrumentForm(forms.ModelForm):
    """
    Форма для создания и редактирования записей об инструментах в административном интерфейсе.

    Предоставляет интерфейс для ручного управления инструментами, включая:
    - Текстовое описание с результатами YOLO анализа
    - Загрузку изображений с аннотациями детекции
    - Указание ожидаемого количества объектов для распознавания
    - Сохранение оригинального имени файла

    Используется в Django Admin для CRUD операций с инструментами.
    """

    class Meta:
        """
        Мета-класс для конфигурации формы.

        Определяет связанную модель, отображаемые поля и их настройки
        для оптимального пользовательского опыта в административном интерфейсе.
        """

        model = Instrument
        fields = (
            'text',
            'image',
            'expected_objects',
            'filename',
            'expected_confidence',
        )

        widgets = {
            'text': forms.Textarea(
                attrs={
                    'rows': 4,
                    'cols': 80,
                    'placeholder': 'Введите описание инструментов и результаты анализа YOLO...',
                }
            ),
            'expected_objects': forms.NumberInput(
                attrs={'min': 1, 'max': 50, 'step': 1, 'placeholder': '11'}
            ),
            'expected_confidence': forms.NumberInput(
                attrs={
                    'min': 0.0,
                    'max': 1.0,
                    'step': 0.01,
                    'placeholder': '0.90',
                }
            ),
            'filename': forms.TextInput(
                attrs={
                    'placeholder': 'Введите оригинальное имя файла...',
                    'maxlength': 255,
                }
            ),
        }

        help_texts = {
            'expected_objects': 'Количество предметов, которые должны быть распознаны на изображении (по умолчанию 11)',
            'expected_confidence': 'Минимальный уровень уверенности для детекции объектов (от 0.0 до 1.0, по умолчанию 0.90)',
            'filename': 'Оригинальное имя файла изображения при загрузке через API',
            'text': 'Описание инструментов с результатами анализа YOLO и мета-информацией',
            'image': 'Изображение с bounding boxes и аннотациями детекции объектов',
        }

        labels = {
            'expected_objects': 'Ожидаемое количество объектов',
            'expected_confidence': 'Ожидаемая уверенность распознавания',
            'filename': 'Исходное имя файла',
            'text': 'Текст записи',
            'image': 'Изображение инструмента',
        }

    def clean_expected_confidence(self):
        """
        Валидация поля expected_confidence.
        """
        expected_confidence = self.cleaned_data.get('expected_confidence')

        if expected_confidence is not None:
            if expected_confidence < 0.0 or expected_confidence > 1.0:
                raise forms.ValidationError(
                    "Уверенность распознавания должна быть в диапазоне от 0.0 до 1.0"
                )

        return expected_confidence

    def clean_expected_objects(self):
        """
        Валидация поля expected_objects.
        """
        expected_objects = self.cleaned_data.get('expected_objects')

        if expected_objects is not None and expected_objects <= 0:
            raise forms.ValidationError(
                "Количество объектов должно быть положительным числом"
            )

        return expected_objects

from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import models


User = get_user_model()


class Instrument(models.Model):
    """
    Модель для хранения записей об инструментах с изображениями.

    Содержит информацию о инструментах, включая текстовое описание,
    изображение и метаданные. Поддерживает анализ изображений через YOLO.
    """

    text = models.TextField(
        help_text="Текст записи с описанием инструментов и результатами анализа YOLO",
        verbose_name="Текст записи",
    )

    pub_date = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name="Дата и время создания"
    )

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='instruments',
        verbose_name="Сотрудник",
        help_text="Сотрудник, создавший запись",
    )

    image = models.ImageField(
        verbose_name="Изображение инструмента",
        upload_to='instruments/',
        help_text="Изображение с аннотациями детекции YOLO",
    )

    expected_objects = models.PositiveIntegerField(
        verbose_name="Ожидаемое количество объектов",
        help_text="Количество предметов, которые должны быть распознаны на изображении",
        default=11,
        blank=True,
    )

    filename = models.CharField(
        verbose_name="Исходное имя файла",
        max_length=255,
        blank=True,
        null=True,
        help_text="Оригинальное имя файла изображения при загрузке",
    )

    class Meta:
        verbose_name = "Запись"
        verbose_name_plural = "Записи"
        ordering = ('-pub_date',)

    def __str__(self) -> str:
        """
        Строковое представление записи.

        Returns:
            str: Первые SLICE_LETTERS символов текста записи
        """
        return self.text[: settings.SLICE_LETTERS]

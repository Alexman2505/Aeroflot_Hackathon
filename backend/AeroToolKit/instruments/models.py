from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import models


User = get_user_model()


class Instrument(models.Model):
    text = models.TextField(
        help_text="Новая запись в базу", verbose_name="Текст записи"
    )
    pub_date = models.DateTimeField(auto_now_add=True, db_index=True)
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='instruments',
        verbose_name="Сотрудник",
    )

    image = models.ImageField(
        verbose_name="Изображение инструмента",
        upload_to='instruments/',
    )

    class Meta:
        verbose_name = "Запись"
        verbose_name_plural = "Записи"
        ordering = ('-pub_date',)

    def __str__(self) -> str:
        return self.text[: settings.SLICE_LETTERS]

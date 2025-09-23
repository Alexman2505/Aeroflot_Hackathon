from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import models


User = get_user_model()


class Group(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы"

    def __str__(self) -> str:
        return self.title


class Instrument(models.Model):
    text = models.TextField(
        help_text="Новая запись в базу", verbose_name="Текст записи"
    )
    pub_date = models.DateTimeField(auto_now_add=True, db_index=True)
    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='instruments',
        verbose_name="Сотрудник",
    )
    group = models.ForeignKey(
        'Group',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='instruments',
        help_text="Группа, к которой будет относиться инструмент",
        verbose_name="Группа",
    )
    image = models.ImageField(
        verbose_name="Изображение инструмента",
        upload_to='instruments/',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Запись"
        verbose_name_plural = "Записи"
        ordering = ('-pub_date',)

    def __str__(self) -> str:
        return self.text[: settings.SLICE_LETTERS]

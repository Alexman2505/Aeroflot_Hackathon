from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    employee_id = models.CharField(
        max_length=20, unique=True, verbose_name="Табельный номер"
    )
    department = models.CharField(
        max_length=100, blank=True, verbose_name="Отдел"
    )
    position = models.CharField(
        max_length=100, blank=True, verbose_name="Должность"
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

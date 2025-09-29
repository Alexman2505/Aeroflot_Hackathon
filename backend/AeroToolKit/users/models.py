from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    Кастомная модель пользователя, расширяющая стандартную модель Django.

    Наследует все поля и методы от AbstractUser и добавляет дополнительные поля
    для учета сотрудников компании.

    Attributes:
        email (EmailField): Электронная почта пользователя
        employee_id (CharField): Уникальный табельный номер сотрудника
        department (CharField): Отдел или подразделение сотрудника
        position (CharField): Должность сотрудника в компании
    """

    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email",
        help_text="Электронная почта сотрудника",
    )
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Табельный номер",
        help_text="Уникальный идентификационный номер сотрудника в системе",
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Отдел",
        help_text="Подразделение или отдел, в котором работает сотрудник",
    )
    position = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Должность",
        help_text="Должность сотрудника в организации",
    )

    class Meta:
        """
        Метаданные модели пользователя.

        Attributes:
            verbose_name (str): Человекочитаемое имя модели в единственном числе
            verbose_name_plural (str): Человекочитаемое имя модели во множественном числе
        """

        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        """
        Строковое представление объекта пользователя.

        Returns:
            str: Строка в формате "username (employee_id)"
        """
        return f'Сотрудник {self.first_name} {self.last_name}'

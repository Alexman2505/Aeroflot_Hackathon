from django.contrib import admin
from .models import Instrument


class InstrumentAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели Instrument.

    Настраивает отображение и функциональность списка инструментов
    в панели администратора Django для удобного управления записями.

    Attributes:
        list_display: Поля, отображаемые в списке записей
        search_fields: Поля, по которым осуществляется поиск
        list_filter: Поля для фильтрации списка записей
        empty_value_display: Замена для пустых значений
    """

    list_display = (
        'pk',
        'text',
        'pub_date',
        'employee',
        'expected_objects',
        'filename',
    )

    search_fields = (
        'text',
        'employee__username',
        'filename',
    )

    list_filter = (
        'pub_date',
        'expected_objects',
        'employee',
    )

    # Поля, отображаемые в форме редактирования
    fieldsets = (
        ('Основная информация', {'fields': ('text', 'employee', 'pub_date')}),
        ('Изображение и файл', {'fields': ('image', 'filename')}),
        (
            'Параметры распознавания',
            {
                'fields': ('expected_objects',),
                'description': 'Настройки связанные с анализом изображения через YOLO',
            },
        ),
    )

    # Поля только для чтения
    readonly_fields = ('pub_date',)

    empty_value_display = '-пусто-'


admin.site.register(Instrument, InstrumentAdmin)

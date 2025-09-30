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
        'expected_confidence',
        'filename',
    )

    search_fields = (
        'text',
        'employee__username',
        'filename',
        'expected_objects',
    )

    list_filter = (
        'pub_date',
        'expected_objects',
        'expected_confidence',
        'employee',
    )

    # Поля, отображаемые в форме редактирования
    fieldsets = (
        ('Основная информация', {'fields': ('text', 'employee', 'pub_date')}),
        ('Изображение и файл', {'fields': ('image', 'filename')}),
        (
            'Параметры распознавания',
            {
                'fields': ('expected_objects', 'expected_confidence'),
                'description': 'Настройки связанные с анализом изображения через YOLO',
            },
        ),
    )

    readonly_fields = ('pub_date',)  # Поля только для чтения
    empty_value_display = '-пусто-'
    list_per_page = 20  # Количество записей на странице
    list_max_show_all = 100  # Максимальное количество для показа всех
    show_full_result_count = True  # Показывать общее количество


admin.site.register(Instrument, InstrumentAdmin)

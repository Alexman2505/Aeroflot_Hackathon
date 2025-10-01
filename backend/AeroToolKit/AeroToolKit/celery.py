import os
from celery import Celery

# Установка переменной окружения для настроек Django по умолчанию
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AeroToolKit.settings')

# Создание экземпляра Celery приложения
app = Celery('AeroToolKit')

"""
Конфигурация Celery для Django приложения AeroToolKit.

Этот модуль инициализирует и настраивает Celery для работы с Django проектом.
Обеспечивает интеграцию фоновых задач с основным приложением.

Основные функции:
- Инициализация Celery приложения с именем проекта
- Загрузка конфигурации из Django settings
- Автоматическое обнаружение задач в установленных приложениях

Configuration:
- Настройки загружаются из Django settings с префиксом CELERY_
- Автоматически обнаруживает задачи в apps из INSTALLED_APPS
- Использует Redis в качестве брокера сообщений и бэкенда результатов

Usage:
- Импортируется в __init__.py пакета для регистрации в Django
- Используется Celery workers для выполнения фоновых задач
- Интегрируется с Django через shared_task декоратор

Example:
    # В tasks.py приложения
    from celery import shared_task

    @shared_task
    def process_instrument_with_yolo(instrument_id, image_data, ...):
        # Фоновая обработка инструмента
        pass
"""

# Загрузка конфигурации из Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

"""
Загружает конфигурацию Celery из настроек Django.

Конфигурационные параметры должны быть определены в settings.py
с префиксом CELERY_ (например: CELERY_BROKER_URL, CELERY_RESULT_BACKEND).

Parameters:
    namespace='CELERY': Префикс для поиска настроек в Django settings

Expected Settings:
    CELERY_BROKER_URL: URL брокера сообщений (redis://redis:6379/0)
    CELERY_RESULT_BACKEND: Бэкенд для хранения результатов задач
    CELERY_TASK_ROUTES: Маршрутизация задач по очередям
    CELERY_ACCEPT_CONTENT: Поддерживаемые форматы сериализации
    CELERY_TASK_SERIALIZER: Формат сериализации задач
"""

# Автоматическое обнаружение задач в установленных приложениях Django
app.autodiscover_tasks()

"""
Автоматически обнаруживает и регистрирует задачи Celery в приложениях Django.

Ищет модули tasks.py во всех приложениях, указанных в INSTALLED_APPS,
и регистрирует все функции, помеченные декоратором @shared_task.

Discovery Process:
1. Сканирует все приложения из INSTALLED_APPS
2. Ищет модули tasks.py в каждом приложении
3. Регистрирует задачи с декоратором @shared_task
4. Связывает задачи с текущим Celery приложением

Registered Tasks:
- api.tasks.process_instrument_with_yolo: Обработка инструментов через YOLO
- Другие задачи из modules tasks.py установленных приложений

Note:
    Для корректной работы необходимо импортировать app в __init__.py пакета:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
"""

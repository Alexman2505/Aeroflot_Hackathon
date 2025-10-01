import os
from celery import Celery

# Установка переменной окружения для настроек Django по умолчанию
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'image_service.settings')

"""
Инициализация Celery приложения для Django проекта image_service.

Этот модуль настраивает Celery для работы с Django приложением photo service.
Обеспечивает интеграцию фоновых задач с основным приложением и настройку
временных зон для корректной работы планировщика задач.

Основные функции:
- Инициализация Celery приложения с именем проекта
- Загрузка конфигурации из Django settings с префиксом CELERY_
- Автоматическое обнаружение задач в установленных приложениях
- Настройка временной зоны и UTC режима

Configuration:
- Настройки загружаются из Django settings с префиксом CELERY_
- Автоматически обнаруживает задачи в apps из INSTALLED_APPS
- Использует Redis в качестве брокера сообщений и бэкенда результатов
- Временная зона синхронизируется с настройками Django

Usage:
- Импортируется в __init__.py пакета для регистрации в Django
- Используется Celery workers для выполнения фоновых задач
- Интегрируется с Django через shared_task декоратор

Example:
    # В tasks.py приложения
    from celery import shared_task

    @shared_task
    def send_single_image(temp_file_path, token, user_data):
        # Фоновая отправка изображения в основной бэкенд
        pass
"""

# Создание экземпляра Celery приложения с именем проекта
app = Celery('image_service')

# Загрузка конфигурации из Django settings с префиксом CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

"""
Загружает конфигурацию Celery из настроек Django проекта.

Конфигурационные параметры должны быть определены в settings.py
с префиксом CELERY_ для корректного распознавания.

Parameters:
    namespace='CELERY': Префикс для поиска настроек в Django settings

Expected Settings in image_service/settings.py:
    CELERY_BROKER_URL: URL брокера сообщений (redis://redis:6379/0)
    CELERY_RESULT_BACKEND: Бэкенд для хранения результатов задач
    CELERY_TASK_DEFAULT_QUEUE: Очередь по умолчанию ('photo_tasks')
    CELERY_TASK_ROUTES: Маршрутизация задач по очередям
    CELERY_ACCEPT_CONTENT: Поддерживаемые форматы сериализации (['json'])
    CELERY_TASK_SERIALIZER: Формат сериализации задач ('json')
    CELERY_RESULT_SERIALIZER: Формат сериализации результатов ('json')
    CELERY_TIMEZONE: Временная зона ('Europe/Moscow')
    CELERY_ENABLE_UTC: Использование UTC времени (False)

Note:
    Все настройки автоматически преобразуются из CELERY_* в соответствующие
    атрибуты объекта Celery (например: CELERY_BROKER_URL → app.conf.broker_url)
"""

# Автоматическое обнаружение задач в установленных приложениях Django
app.autodiscover_tasks()

"""
Автоматически обнаруживает и регистрирует задачи Celery в приложениях Django.

Ищет модули tasks.py во всех приложениях, указанных в INSTALLED_APPS,
и регистрирует все функции, помеченные декоратором @shared_task.

Discovery Process:
1. Сканирует все приложения из INSTALLED_APPS проекта image_service
2. Ищет модули tasks.py в каждом приложении
3. Регистрирует задачи с декоратором @shared_task
4. Связывает задачи с текущим Celery приложением

Registered Tasks:
- api.tasks.send_single_image: Отправка одного изображения в основной бэкенд
- api.tasks.process_image_batch: Устаревшая задача пакетной обработки
- Другие задачи из modules tasks.py установленных приложений

Note:
    Для корректной работы необходимо импортировать app в __init__.py пакета:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
"""

# Настройка временной зоны и UTC режима из конфигурации Django
app.conf.timezone = app.conf.CELERY_TIMEZONE
app.conf.enable_utc = app.conf.CELERY_ENABLE_UTC

"""
Настраивает временную зону и режим UTC для корректной работы планировщика задач.

Важно для:
- Корректного расчета времени выполнения отложенных задач
- Синхронизации времени между разными сервисами
- Правильного логирования временных меток

Configuration:
- timezone: Устанавливается из CELERY_TIMEZONE ('Europe/Moscow')
- enable_utc: Устанавливается из CELERY_ENABLE_UTC (False)

Note:
    Временная зона должна совпадать с TIME_ZONE в настройках Django
    для избежания расхождений во времени между компонентами системы.
"""

# Повторное обнаружение задач для обеспечения полной регистрации
app.autodiscover_tasks()

"""
Повторное обнаружение задач для гарантии полной регистрации всех задач.

Дублирующий вызов обеспечивает, что все задачи будут зарегистрированы,
даже если некоторые приложения были загружены после первого вызова.

Safety Measure:
- Гарантирует регистрацию задач из всех приложений
- Защищает от проблем с порядком загрузки приложений
- Обеспечивает надежность в различных средах выполнения

Note:
    В большинстве случаев одного вызова достаточно, но повторный вызов
    добавляет дополнительную надежность в production средах.
"""

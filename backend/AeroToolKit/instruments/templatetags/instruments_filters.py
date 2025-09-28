import re
from django import template

register = template.Library()


@register.filter(name='extract_detected_count_filter')
def extract_detected_count(text):
    """
    Извлекает количество распознанных объектов из текста YOLO анализа.

    Ищет в тексте паттерн "YOLO анализ: обнаружено X объектов"
    и возвращает количество X.

    Args:
        text (str): Текст записи с результатами YOLO анализа

    Returns:
        int: Количество распознанных объектов или 0 если не найдено
    """
    if not text:
        return 0

    # Ищем паттерн "обнаружено X объектов"
    pattern = r'обнаружено\s+(\d+)\s+объект'
    match = re.search(pattern, text)

    if match:
        return int(match.group(1))

    # Альтернативный поиск если первый не сработал
    pattern_alt = r'YOLO анализ: обнаружено (\d+) объектов'
    match_alt = re.search(pattern_alt, text)

    if match_alt:
        return int(match_alt.group(1))

    return 0

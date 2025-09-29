from django.conf import settings
from django.core.paginator import Paginator


def make_page(request, instruments):
    """
    Создает пагинированную страницу для списка инструментов.

    Функция-утилита для обработки пагинации queryset инструментов.
    Использует настройки из settings.NUMBER_OF_INSTRUMENTS для определения
    количества элементов на странице.

    Args:
        request: HTTP запрос от пользователя, содержащий параметр 'page' для пагинации
        instruments (QuerySet): Набор данных инструментов для пагинации

    Returns:
        Page: Объект страницы пагинатора с инструментами для текущей страницы

    Example:
        >>> page_obj = make_page(request, Instrument.objects.all())
        >>> for instrument in page_obj:
        ...     print(instrument.text)

    Notes:
        - Если параметр 'page' не указан в запросе, возвращается первая страница
        - Если указан невалидный номер страницы, возвращается первая страница
        - Если указана страница за пределами диапазона, возвращается последняя страница
    """
    paginator = Paginator(instruments, settings.NUMBER_OF_INSTRUMENTS)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)

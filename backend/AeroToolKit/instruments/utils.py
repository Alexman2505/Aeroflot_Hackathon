from django.conf import settings
from django.core.paginator import Paginator


def make_page(request, instruments):
    paginator = Paginator(instruments, settings.NUMBER_OF_INSTRUMENTS)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)

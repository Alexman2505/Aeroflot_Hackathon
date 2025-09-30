from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from .models import Instrument, User
from .forms import InstrumentForm
from .utils import make_page


@login_required
def instrument_create(request):
    """
    Создание новой записи об инструменте под авторизацией пользователя.

    Обрабатывает GET и POST запросы для создания инструмента:
    - GET: Отображает пустую форму для создания инструмента
    - POST: Валидирует и сохраняет данные формы, назначает текущего пользователя как сотрудника

    Args:
        request: HTTP запрос от пользователя

    Returns:
        HttpResponse: Страница с формой создания или редирект на главную страницу при успехе

    Raises:
        PermissionDenied: Если пользователь не аутентифицирован
    """
    if request.method == "POST":
        form = InstrumentForm(request.POST, files=request.FILES or None)
        if form.is_valid():
            instrument = form.save(commit=False)
            instrument.employee = request.user
            instrument.save()
            return redirect('instruments:index')
    form = InstrumentForm()
    return render(
        request,
        'instruments/create_instrument.html',
        {
            'form': form,
        },
    )


@login_required
def instrument_edit(request, instrument_id):
    """
    Редактирование существующей записи об инструменте под авторизацией.

    Проверяет права доступа пользователя к редактированию инструмента:
    - Только автор инструмента может его редактировать
    - При попытке редактирования чужого инструмента выполняется редирект на детальную страницу

    Args:
        request: HTTP запрос от пользователя
        instrument_id (int): ID редактируемого инструмента

    Returns:
        HttpResponse: Страница с формой редактирования или редирект при отсутствии прав

    Raises:
        Http404: Если инструмент с указанным ID не существует
        PermissionDenied: Если пользователь не аутентифицирован
    """
    instrument = get_object_or_404(Instrument, pk=instrument_id)
    if instrument.employee != request.user:
        return redirect('instruments:instrument_detail', instrument_id)
    form = InstrumentForm(
        request.POST or None, files=request.FILES or None, instance=instrument
    )
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('instruments:instrument_detail', instrument_id)
    return render(
        request,
        'instruments/create_instrument.html',
        {'form': form, 'is_edit': True},
    )


def index(request):
    """
    Главная страница приложения со списком всех инструментов.

    Отображает пагинированный список всех инструментов в системе.
    Использует оптимизацию запросов через select_related для избежания N+1 проблемы.

    Args:
        request: HTTP запрос от пользователя

    Returns:
        HttpResponse: Главная страница с пагинированным списком инструментов
    """
    instruments = Instrument.objects.select_related('employee')
    return render(
        request,
        'instruments/index.html',
        {
            'page_obj': make_page(request, instruments),
            'employee': request.user,
        },
    )


def profile(request, username):
    """
    Страница профиля пользователя с его инструментами.

    Отображает профиль указанного пользователя и список всех его инструментов.
    Если пользователь не существует, возвращает 404 ошибку.

    Args:
        request: HTTP запрос от пользователя
        username (str): Имя пользователя для отображения профиля

    Returns:
        HttpResponse: Страница профиля пользователя с его инструментами

    Raises:
        Http404: Если пользователь с указанным username не существует
    """
    employee = get_object_or_404(User, username=username)
    instruments = Instrument.objects.select_related('employee').filter(
        employee__username=username
    )
    return render(
        request,
        'instruments/profile.html',
        {
            'employee': employee,
            'page_obj': make_page(request, instruments),
        },
    )


def instrument_detail(request, instrument_id):
    """
    Детальная страница конкретного инструмента.

    Отображает полную информацию об инструменте включая:
    - Текст описания с результатами YOLO анализа
    - Изображение с аннотациями
    - Мета-информацию (автор, дата создания, ожидаемое количество объектов)

    Args:
        request: HTTP запрос от пользователя
        instrument_id (int): ID инструмента для отображения

    Returns:
        HttpResponse: Детальная страница инструмента

    Raises:
        Http404: Если инструмент с указанным ID не существует
    """
    instrument = get_object_or_404(
        Instrument.objects.select_related('employee'),
        pk=instrument_id,
    )
    employee = request.user.pk
    return render(
        request,
        'instruments/instrument_detail.html',
        {
            'instrument': instrument,
            'employee': employee,
        },
    )


@login_required
def instrument_delete(request, instrument_id):
    """
    Удаление записи об инструменте под авторизацией пользователя.

    Проверяет права доступа пользователя на удаление инструмента:
    - Только автор инструмента может его удалить
    - При попытке удаления чужого инструмента выполняется редирект на детальную страницу
    - Подтверждение удаления происходит через POST запрос

    Args:
        request: HTTP запрос от пользователя
        instrument_id (int): ID инструмента для удаления

    Returns:
        HttpResponse:
            - Страница подтверждения удаления (GET)
            - Редирект на главную страницу после успешного удаления (POST)
            - Редирект на детальную страницу при отсутствии прав доступа

    Raises:
        Http404: Если инструмент с указанным ID не существует
        PermissionDenied: Если пользователь не аутентифицирован
    """
    instrument = get_object_or_404(Instrument, pk=instrument_id)
    if instrument.employee != request.user:
        return redirect(
            'instruments:instrument_detail', instrument_id=instrument_id
        )
    if request.method == "POST":
        instrument.delete()
        return redirect('instruments:index')
    return render(
        request,
        'instruments/confirm_delete.html',
        {'instrument': instrument},
    )

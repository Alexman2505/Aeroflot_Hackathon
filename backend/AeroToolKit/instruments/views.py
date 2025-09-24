from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect

from .models import Group, Instrument, User
from .forms import InstrumentForm
from .utils import make_page


@login_required
def instrument_create(request):
    '''Создание записи под авторизацией.'''
    if request.method == "POST":
        form = InstrumentForm(request.POST, files=request.FILES or None)
        if form.is_valid():
            instrument = form.save(commit=False)
            instrument.employee = request.user
            instrument.save()
            return redirect('instruments:profile', request.user)
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
    '''Редактирование записи под авторизацией.'''
    instrument = get_object_or_404(Instrument, id=instrument_id)
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
    '''Главная страница c кешем 20 секунд.'''
    instruments = Instrument.objects.select_related('group', 'employee')
    return render(
        request,
        'instruments/index.html',
        {
            'page_obj': make_page(request, instruments),
            'employee': request.user,
        },
    )


def group_instruments(request, slug):
    '''Страница групп.'''
    group = get_object_or_404(Group, slug=slug)
    instruments = group.instruments.select_related('employee')
    return render(
        request,
        'instruments/group_instruments.html',
        {'group': group, 'page_obj': make_page(request, instruments)},
    )


def profile(request, username):
    '''Страница профиля пользователя.'''
    employee = get_object_or_404(User, username=username)
    instruments = Instrument.objects.select_related(
        'group', 'employee'
    ).filter(employee__username=username)
    return render(
        request,
        'instruments/profile.html',
        {
            'employee': employee,
            'page_obj': make_page(request, instruments),
        },
    )


def instrument_detail(request, instrument_id):
    '''Отдельная запись.'''
    instrument = get_object_or_404(
        Instrument.objects.select_related('employee', 'group'),
        id=instrument_id,
    )
    employee = request.user.id
    return render(
        request,
        'instruments/instrument_detail.html',
        {
            'instrument': instrument,
            'employee': employee,
        },
    )

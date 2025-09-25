from django.contrib import admin

from .models import Instrument


class InstrumentAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'text',
        'pub_date',
        'employee',
    )

    search_fields = ('text',)
    list_filter = ('pub_date',)
    empty_value_display = '-пусто-'


admin.site.register(Instrument, InstrumentAdmin)

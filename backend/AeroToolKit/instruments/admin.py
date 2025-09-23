from django.contrib import admin

from .models import Group, Instrument


class InstrumentAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'text',
        'pub_date',
        'employee',
        'group',
    )
    list_editable = ('group',)
    search_fields = ('text',)
    list_filter = ('pub_date',)
    empty_value_display = '-пусто-'


class GroupAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'slug',
        'description',
    )
    search_fields = ('text',)
    empty_value_display = '-пусто-'


admin.site.register(Instrument, InstrumentAdmin)
admin.site.register(Group, GroupAdmin)

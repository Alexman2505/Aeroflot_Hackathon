from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model


User = get_user_model()


class CreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'first_name',
            'last_name',
            'username',
            'employee_id',
            'department',
            'position',
        )


def clean_subject(self):
    data = self.cleaned_data['subject']
    if 'спасибо' not in data.lower():
        raise forms.ValidationError('Вы обязательно должны нас поблагодарить!')
    return data

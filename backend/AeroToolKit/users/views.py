from django.shortcuts import render, redirect
from django.views.generic import CreateView
from django.urls import reverse_lazy
from .forms import CreationForm, ContactForm


class SignUp(CreateView):
    form_class = CreationForm
    success_url = reverse_lazy('instruments:index')
    template_name = 'users/signup.html'


def user_contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('')
        return render(request, 'users/contact.html', {'form': form})
    form = ContactForm()
    return render(request, 'users/contact.html', {'form': form})

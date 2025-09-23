from django.views.generic.base import TemplateView


class AboutTeamView(TemplateView):
    template_name = 'team/team.html'


class AboutTechView(TemplateView):
    template_name = 'team/tech.html'

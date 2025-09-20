# api/views.py
from rest_framework import viewsets
from rest_framework.response import Response


class ToolViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"message": "API работает!"})

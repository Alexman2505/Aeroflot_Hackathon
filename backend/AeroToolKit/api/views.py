from django.contrib.auth import authenticate
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import SearchFilter, OrderingFilter
from instruments.models import Instrument
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import InstrumentSerializer, InstrumentCreateSerializer


class ToolViewSet(viewsets.ViewSet):
    """Вьюсет для проверки работы API"""

    def list(self, request):
        return Response({"message": "API работает!"})


class InstrumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с инструментами.
    Вся логика создания в сериализаторе.
    """

    queryset = Instrument.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # Фильтрация, поиск, сортировка
    filterset_fields = ['employee', 'pub_date']
    search_fields = ['text', 'employee__username']
    ordering_fields = ['pub_date', 'id', 'employee__username']
    ordering = ['-pub_date']

    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от действия"""
        if self.action == 'create':
            return InstrumentCreateSerializer
        return InstrumentSerializer

    def get_queryset(self):
        """Оптимизация запросов"""
        return super().get_queryset().select_related('employee')

    @swagger_auto_schema(
        operation_description="Создание инструмента с обязательной загрузкой изображения в base64",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['text', 'full_base64_string'],
            properties={
                'text': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Описание инструмента (обязательно)",
                    example="Фотография набора инструментов",
                ),
                'full_base64_string': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Изображение в формате base64 (обязательно)",
                    example="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAA...",
                ),
            },
        ),
        responses={
            201: openapi.Response('Успешно создано', InstrumentSerializer),
            400: openapi.Response('Ошибка валидации'),
        },
    )
    def create(self, request, *args, **kwargs):
        """
        Создание инструмента.
        Вся логика в сериализаторе - просто вызываем родительский метод.
        """
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        Вызывается после валидации.
        Вся логика уже в сериализаторе, просто сохраняем.
        """
        serializer.save()


@api_view(['POST'])
@permission_classes([AllowAny])
def obtain_auth_token_csrf_exempt(request):
    """
    Упрощенная CSRF-экземпempt версия получения токена.
    """

    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(username=username, password=password)

    if user:
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})
    else:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_400_BAD_REQUEST,
        )

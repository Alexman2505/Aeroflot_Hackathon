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
    """
    Вьюсет для проверки работоспособности API.
    Предоставляет простой endpoint для проверки доступности API сервиса.
    """

    @swagger_auto_schema(
        operation_description="Проверка работоспособности API сервиса",
        operation_summary="Проверка API",
        responses={
            200: openapi.Response(
                'API работает',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    },
                ),
            )
        },
    )
    def list(self, request):
        """
        Возвращает простое сообщение о работоспособности API.
        Returns:
            Response: JSON ответ с сообщением о статусе API
        """
        return Response({"message": "API работает!"})


class InstrumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для CRUD операций с инструментами.

    Обеспечивает полный набор операций для работы с инструментами:
    создание, чтение, обновление, удаление. Вся бизнес-логика создания
    инструментов инкапсулирована в сериализаторе.

    Attributes:
        queryset: Базовый queryset для операций с БД
        authentication_classes: Использует токен-аутентификацию
        permission_classes: Требует аутентификации для всех операций
        filter_backends: Поддерживает фильтрацию, поиск и сортировку
    """

    queryset = Instrument.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # Фильтрация, поиск, сортировка
    filterset_fields = [
        'employee',
        'employee__username',
        'pub_date',
        'filename',
        'expected_objects',
        'expected_confidence',
    ]
    search_fields = [
        'text',
        'employee__username',
        'pub_date',
        'expected_objects',
        'expected_confidence',
    ]
    ordering_fields = [
        'id',
        'text',
        'employee__username',
        'pub_date',
        'expected_objects',
        'expected_confidence',
    ]
    ordering = ['-pub_date']

    def get_serializer_class(self):
        """
        Выбирает соответствующий сериализатор в зависимости от действия.

        Для создания инструмента используется InstrumentCreateSerializer,
        который включает специальную логику обработки base64 изображений.
        Для остальных операций используется базовый InstrumentSerializer.

        Returns:
            Serializer: Выбранный класс сериализатора
        """
        if self.action == 'create':
            return InstrumentCreateSerializer
        return InstrumentSerializer

    def get_queryset(self):
        """
        Оптимизирует запросы к базе данных.

        Использует select_related для избежания N+1 проблемы при загрузке
        связанных данных пользователя.

        Returns:
            QuerySet: Оптимизированный queryset с предзагрузкой связанных объектов
        """
        return super().get_queryset().select_related('employee')

    @swagger_auto_schema(
        operation_description="Создание инструмента с загрузкой бинарного изображения",
        operation_summary="Создание инструмента",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[
                'text',
                'image',
                'expected_objects',
                'expected_confidence',
            ],
            properties={
                'text': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Описание инструмента (обязательно)",
                    example="Фотография набора инструментов",
                ),
                'image': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="Бинарный файл изображения (обязательно)",
                ),
                'filename': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Исходное имя файла (опционально)",
                    example="DSCN4946.JPG",
                ),
                'expected_objects': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Ожидаемое количество объектов (обязательно)",
                    example=11,
                ),
                'expected_confidence': openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    description="Ожидаемая уверенность распознавания (обязательно)",
                    example=0.9,
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
        Создает новый инструмент с обработкой изображения через YOLO.

        Основная логика создания находится в сериализаторе InstrumentCreateSerializer,
        который обрабатывает base64 изображение, выполняет детекцию объектов через YOLO
        и сохраняет аннотированное изображение.

        Args:
            request: HTTP запрос с данными для создания инструмента
            *args: Дополнительные позиционные аргументы
            **kwargs: Дополнительные именованные аргументы

        Returns:
            Response: Ответ с созданным объектом или ошибками валидации
        """
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        Выполняется после успешной валидации данных.

        Поскольку вся бизнес-логика создания уже реализована в сериализаторе,
        метод просто сохраняет объект в базу данных.

        Args:
            serializer: Валидированный сериализатор с данными для сохранения
        """
        serializer.save()

    @swagger_auto_schema(
        operation_description="Получить список всех инструментов с поддержкой фильтрации, поиска и сортировки",
        operation_summary="Список инструментов",
        responses={
            200: openapi.Response(
                'Успешный ответ', InstrumentSerializer(many=True)
            ),
            401: openapi.Response('Требуется аутентификация'),
        },
    )
    def list(self, request, *args, **kwargs):
        """Получить пагинированный список инструментов"""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Получить детальную информацию о конкретном инструменте по ID",
        operation_summary="Детальная информация об инструменте",
        responses={
            200: openapi.Response('Успешный ответ', InstrumentSerializer),
            404: openapi.Response('Инструмент не найден'),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        """Получить инструмент по ID"""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Полное обновление инструмента. Все поля обязательны.",
        operation_summary="Полное обновление инструмента",
        request_body=InstrumentSerializer,
        responses={
            200: openapi.Response('Успешное обновление', InstrumentSerializer),
            400: openapi.Response('Ошибка валидации'),
            404: openapi.Response('Инструмент не найден'),
        },
    )
    def update(self, request, *args, **kwargs):
        """Полное обновление инструмента"""
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Частичное обновление инструмента. Только указанные поля будут обновлены.",
        operation_summary="Частичное обновление инструмента",
        request_body=InstrumentSerializer,
        responses={
            200: openapi.Response('Успешное обновление', InstrumentSerializer),
            400: openapi.Response('Ошибка валидации'),
            404: openapi.Response('Инструмент не найден'),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        """Частичное обновление инструмента"""
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Удаление инструмента по ID",
        operation_summary="Удаление инструмента",
        responses={
            204: openapi.Response('Успешное удаление'),
            404: openapi.Response('Инструмент не найден'),
        },
    )
    def destroy(self, request, *args, **kwargs):
        """Удалить инструмент"""
        return super().destroy(request, *args, **kwargs)


@swagger_auto_schema(
    method='post',
    operation_description="Получение аутентификационного токена для доступа к API",
    operation_summary="Получение токена аутентификации",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['username', 'password'],
        properties={
            'username': openapi.Schema(
                type=openapi.TYPE_STRING, description='Имя пользователя'
            ),
            'password': openapi.Schema(
                type=openapi.TYPE_STRING, description='Пароль'
            ),
        },
    ),
    responses={
        200: openapi.Response(
            'Успешная аутентификация',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={'token': openapi.Schema(type=openapi.TYPE_STRING)},
            ),
        ),
        400: openapi.Response('Ошибка валидации'),
        401: openapi.Response('Неверные учетные данные'),
    },
)
@api_view(['POST'])
@permission_classes([AllowAny])
def obtain_auth_token_csrf_exempt(request):
    """
    Упрощенная CSRF-экземптная версия получения аутентификационного токена.

    Предназначена для использования внешними клиентами и сервисами,
    которые не могут работать с CSRF токенами Django.

    Args:
        request: HTTP POST запрос с данными аутентификации

    Returns:
        Response: JSON ответ с токеном аутентификации или ошибкой

    Example:
        POST /api-token-auth/
        {
            "username": "user@example.com",
            "password": "password123"
        }

        Response:
        {
            "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
        }
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

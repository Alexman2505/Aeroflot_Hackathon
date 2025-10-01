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
import time
import sys


class ToolViewSet(viewsets.ViewSet):
    """
    Вьюсет для проверки работоспособности API.
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
        return Response({"message": "API работает!"})


class InstrumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для CRUD операций с инструментами.
    """

    queryset = Instrument.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

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
        if self.action == 'create':
            return InstrumentCreateSerializer
        return InstrumentSerializer

    def get_queryset(self):
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
        """
        print(
            f"🎯 [CREATE START] Время: {time.strftime('%H:%M:%S')}", flush=True
        )
        print(f"📦 [FILES] Ключи: {list(request.FILES.keys())}", flush=True)
        print(f"👤 [USER] {request.user}", flush=True)

        if request.FILES.get('image'):
            image = request.FILES['image']
            print(
                f"🖼️ [IMAGE INFO] Имя: {image.name}, Размер: {image.size} bytes, Тип: {image.content_type}",
                flush=True,
            )

        start_time = time.time()
        print(f"⏱️ [TIMING START] {start_time}", flush=True)

        try:
            response = super().create(request, *args, **kwargs)
            end_time = time.time()
            print(
                f"✅ [CREATE SUCCESS] Время выполнения: {end_time - start_time:.2f} сек",
                flush=True,
            )
            print(f"📊 [RESPONSE] Статус: {response.status_code}", flush=True)
            return response
        except Exception as e:
            end_time = time.time()
            print(
                f"❌ [CREATE ERROR] Время до ошибки: {end_time - start_time:.2f} сек",
                flush=True,
            )
            print(f"💥 [ERROR] {str(e)}", flush=True)
            raise

    def perform_create(self, serializer):
        """
        Выполняется после успешной валидации данных.
        """
        print("🔧 [PERFORM_CREATE] Начало сохранения в БД", flush=True)
        start_time = time.time()
        print(f"⏱️ [DB SAVE START] {start_time}", flush=True)

        serializer.save()

        end_time = time.time()
        print(
            f"💾 [PERFORM_CREATE COMPLETE] Сохранение заняло: {end_time - start_time:.2f} сек",
            flush=True,
        )

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
        print(
            f"📋 [LIST START] Время: {time.strftime('%H:%M:%S')}", flush=True
        )
        print(f"👤 [USER] {request.user}", flush=True)
        print(f"🔍 [QUERY PARAMS] {request.query_params}", flush=True)

        start_time = time.time()
        response = super().list(request, *args, **kwargs)
        end_time = time.time()

        print(
            f"✅ [LIST SUCCESS] Время выполнения: {end_time - start_time:.2f} сек",
            flush=True,
        )
        print(
            f"📊 [RESPONSE ITEMS] {len(response.data) if hasattr(response.data, '__len__') else 'N/A'}",
            flush=True,
        )
        return response


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
    """
    print(f"🔑 [AUTH START] Время: {time.strftime('%H:%M:%S')}", flush=True)
    username = request.data.get('username')
    password = request.data.get('password')

    print(f"👤 [AUTH ATTEMPT] Username: {username}", flush=True)

    if not username or not password:
        print("❌ [AUTH ERROR] Missing username or password", flush=True)
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(username=username, password=password)

    if user:
        token, created = Token.objects.get_or_create(user=user)
        print(
            f"✅ [AUTH SUCCESS] User: {user}, Token created: {created}",
            flush=True,
        )
        return Response({'token': token.key})
    else:
        print("❌ [AUTH FAILED] Invalid credentials", flush=True)
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_400_BAD_REQUEST,
        )

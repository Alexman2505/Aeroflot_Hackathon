import base64
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from instruments.models import Instrument


class ToolViewSet(viewsets.ViewSet):
    """Вьюсет просто для проверки, что апи работает"""

    def list(self, request):
        return Response({"message": "API работает!"})


# Основная логика получения и загрузки изображения по API
class UploadViewSet(viewsets.ViewSet):
    """ViewSet для загрузки изображений через API"""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Загрузка изображения через API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['sender', 'full_base64_string'],
            properties={
                'sender': openapi.Schema(type=openapi.TYPE_STRING),
                'timestamp': openapi.Schema(type=openapi.TYPE_STRING),
                'full_base64_string': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            201: openapi.Response(description='Успешная загрузка'),
            400: openapi.Response(description='Ошибка валидации'),
            403: openapi.Response(description='Доступ запрещен'),
        },
    )
    def create(self, request):
        """
        Загрузка изображения через API

        Пример тела запроса:
        {
            "sender": "username",
            "timestamp": "1727184625",
            "full_base64_string": "data:image/jpeg;base64,..."
        }
        """
        try:
            # Получаем данные из запроса
            sender_username = request.data.get('sender')
            timestamp = request.data.get('timestamp')
            full_base64_string = request.data.get('full_base64_string')

            # Валидация обязательных полей
            if not all([sender_username, full_base64_string]):
                return Response(
                    {
                        'error': 'Отсутствуют обязательные поля: sender, full_base64_string'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Проверяем, что отправитель совпадает с аутентифицированным пользователем
            if request.user.username != sender_username:
                return Response(
                    {
                        'error': 'Имя отправителя не совпадает с аутентифицированным пользователем'
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Парсим base64 строку
            if full_base64_string.startswith('data:image'):
                # Убираем префикс "data:image/format;base64,"
                base64_data = full_base64_string.split(',', 1)[1]
            else:
                base64_data = full_base64_string

            # Декодируем base64
            try:
                image_data = base64.b64decode(base64_data)
            except Exception as e:
                return Response(
                    {'error': f'Ошибка декодирования base64: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Создаем имя файла
            file_extension = 'jpg'
            filename = f"upload_{request.user.username}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"

            # Создаем запись Instrument
            text = f"Автоматическая загрузка от {request.user.username}. \n"
            if timestamp:
                text += f"Время отправки запроса с сервиса photo_server: {timestamp}"

            instrument = Instrument(
                text=text,
                employee=request.user,
                pub_date=timezone.now(),
            )

            # Сохраняем изображение
            instrument.image.save(filename, ContentFile(image_data), save=True)
            instrument.save()

            return Response(
                {
                    'success': True,
                    'instrument_id': instrument.id,
                    'message': 'Изображение успешно загружено',
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {'error': f'Внутренняя ошибка сервера: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

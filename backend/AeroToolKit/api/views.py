import base64

from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated

from instruments.models import Instrument


class ToolViewSet(viewsets.ViewSet):
    """Вьюсет просто для проверки, что апи работает"""

    def list(self, request):
        return Response({"message": "API работает!"})


# Основная логика получения и загрузки изображения по API
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_image_api(request):
    """
    API endpoint для загрузки изображений от photo_server
    Пример JSON:
    {
        "sender": "username",
        "timestamp": "2024-01-01T10:00:00",
        "full_base64_string": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ..."
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
        file_extension = 'jpg'  # или можно определить из MIME type
        filename = f"upload_{request.user.username}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"

        # Создаем запись Instrument
        instrument = Instrument(
            text=f"Автоматическая загрузка от {request.user.username}.",
            employee=request.user,  # Пользователь из токена
            pub_date=timezone.now(),
            # group можно оставить пустым или назначить дефолтную группу
        )

        # Сохраняем изображение
        instrument.image.save(filename, ContentFile(image_data), save=True)

        # Сохраняем запись
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

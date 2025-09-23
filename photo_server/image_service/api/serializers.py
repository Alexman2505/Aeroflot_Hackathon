# пока отключим проверку сериализаторами, файлы руками же загружаются на этом сервисе
# from rest_framework import serializers


# class ExternalAPISerializer(serializers.Serializer):
#     """
#     Сериализатор для подготовки данных отправки на внешний API AeroToolKit.
#     Используется для валидации и сериализации данных перед отправкой
#     на основной сервер обработки изображений.
#     """

#     sender = serializers.CharField(max_length=100)
#     timestamp = serializers.DateTimeField()
#     image_string = serializers.CharField()

# Сервис на питоне 3.10 работает
FROM python:3.10

WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install -r requirements.txt --no-cache-dir

# Копируем проект
COPY . .

# Создаем папки для статики и медиа
RUN mkdir -p staticfiles media

# Создаем папку для временных загрузок
RUN mkdir -p media/temp_uploads

EXPOSE 8000

# Переходим в папку с Django проектом
WORKDIR /app/image_service

CMD ["gunicorn", "image_service.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]

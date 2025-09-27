#Сервис на питоне 3.10 работает
FROM python:3.10

WORKDIR /app

# # Устанавливаем зависимости для PostgreSQL
# RUN apt-get update && apt-get install -y \
#     postgresql-client \
#     netcat-openbsd \
#     && rm -rf /var/lib/apt/lists/*

# Копируем requirements
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install -r requirements.txt --no-cache-dir

# Копируем проект
COPY . .

# Создаем папки для статики и медиа
RUN mkdir -p staticfiles media

EXPOSE 8000

# Переходим в папку с Django проектом
WORKDIR /app/AeroToolKit

CMD ["gunicorn", "AeroToolKit.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]

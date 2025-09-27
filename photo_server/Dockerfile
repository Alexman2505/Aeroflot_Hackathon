#Сервис на питоне 3.10 работает
FROM python:3.10

WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install -r requirements.txt --no-cache-dir

# Копируем проект
COPY . .

# Переходим в папку с Django проектом
WORKDIR /app/image_service

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

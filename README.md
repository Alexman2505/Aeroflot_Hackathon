# AeroToolKit - Система автоматизированного учета инструментов построенная по "клиент-серверной" архитектуре.

## Система развернута на хостинге Yandex Cloud и состоит из [клиента отправки изображений](http://aerotoolkit.sytes.net:8001/) и [сервера с моделью компьютерного зрения](http://aerotoolkit.sytes.net:8000/) для распознавания инструментов и записих их в базу. Всё ПО полностью opensource (список используемых библиотек представлен ниже).

## ВНИМАНИЕ! В данный момент скорость взаимодействия компонентов всей системы ограничена пропуской способностью виртуальной машины яндекса, поэтому - сначала дождитесь появления сообщения об отправки фотографий с [клиента](http://aerotoolkit.sytes.net:8001/), а после - обновляйте страницу сайта [AeroToolKit](http://aerotoolkit.sytes.net:8000/) несколько раз для проверки качества работы.

## Но чтобы ОЦЕНИТЬ РЕАЛЬНУЮ СКОРОСТЬ работы всей системы - запустите её локально в Docker. Система демонстрирует распознавание объектов практически в реальном времени. Быстродействие зависит исключительно от мощности вашего процессора.

## Инструкция (документация) по использованию системы (краткая версия):

1. Зарегистрироваться на [AeroToolKit](http://aerotoolkit.sytes.net:8000/)
2. Ввести логин/пароль от [AeroToolKit](http://aerotoolkit.sytes.net:8000/) на [Photo Server](http://aerotoolkit.sytes.net:8001/), НАСТРОИТЬ ПАРАМЕТРЫ РАСПОЗНАВАНИЯ (!), загрузить и отправить фотографии
3. Вернуться обратно на [AeroToolKit](http://aerotoolkit.sytes.net:8000/) и увидеть результат работы модели компьютерного зрения

## Инструкция (документация) по использованию системы (полная версия) и описание работы.

1. **Регистрация** — создайте учетную запись на основном сайте [AeroToolKit](http://aerotoolkit.sytes.net:8000/). Это сервер обработки изображений с реализованным [api](http://aerotoolkit.sytes.net:8000/api/v1/). Также доступна интерактивная документация [swagger](http://aerotoolkit.sytes.net:8000/api/v1/swagger/) и [redoc](http://aerotoolkit.sytes.net:8000/api/v1/redoc/) После регистрации откроются дополнительные страницы сайта.

2. **Аутентификация** — перейдите на сайт загрузки изображений [Photo Server](http://aerotoolkit.sytes.net:8001/) и введите полученный логин/пароль, указанные при регистрации в AeroToolKit. Сайт Photo Server был реализован с целью демонстрации возможности работы системы по "клиент-серверной" архитектуре. Принцип "разделения ответственности": клиент отправляет изображения, а сервер их получает, распознает, и записывает в базу вместе с метаинформацией об отправителе. Но также вы можете, опираясь на документацию endpoint'ов в api, самостоятельно отправлять запросы через [swagger](http://aerotoolkit.sytes.net:8000/api/v1/swagger/) или [postman](https://www.postman.com/) на основной сайт AeroToolKit

3. **Получение токена** — сервер Photo Server **АВТОМАТИЧЕСКИ** запросит и получит секретный токен доступа у основного сервера AeroToolKit. Сейчас, для демонстрации работы системы, этот токен отображается на главной странице сайта Photo Server в формате `Token 123xxxx...`. Внимание! Оба сайта работают по протоколу http для совместимости с docker-compose.yml файлом. Этот файл потребуется для разворачивания системы через [докер](https://www.docker.com/) на локальной машине или другом хостинге, где предварительно не будет SSL-сертификата для https шифрования.

4. **Загрузка изображений** — на странице Photo Server выберите и загрузите несколько фотографий инструментов. Браузер закодирует изображения в multipart/form-data формат данных (POST /upload/ HTTP/1.1 Content-Type: multipart/form-data), а клиент Photo Server отправит эти изображения на сервер AeroToolKit. В первоначальной версии программы (первые коммиты) была реализована отравка изображений в base64 кодировке (в т.ч. непосредственно в интерактивном swagger), но, с целью демонстрации ускорения работы всей системы, файлы отправляются в формате multipart/form-data.

5. **Асинхронные обработка** - оба сервера ("AeroToolKit Backend" и "Photo Server") реализуют параллельную асинхронную обработку данных через **Celery**. Отдельные, изолированные очереди отвечают за отправку и распознавание инструментов. Такой подход позволяет масштабировать систему для загрузки десятков файлов. Для координации асинхронных операций используется **Redis** — высокопроизводительная in-memory система, работающая как брокер сообщений. Поэтому программу можно адаптировать к любому оборудованию за счет гибкой настройки docker-compose.yml файла в корневой директории репозитория. Сейчас на локальной машине, за счет отсутствия http задержек, мгновенно обрабатывается и распознается 50+ файлов (в зависимости от процессора). Вся операции по распознаванию инструментов производится исключительно на ЦПУ - на виртуальной машине Yandex Cloud попросту нет видеокарты. Это демонстрирует независимость модели от наличия GPU.

6. **Просмотр результатов** — вернитесь на главную страницу [AeroToolKit](http://aerotoolkit.sytes.net:8000/) для просмотра обработанных изображений и результатов их распознавания. Для демонстрации работы СУБД PostgreSQL доступен просмотр всех записей сотрудников, а в административной панели сайта — расширенный поиск, сортировка и фильтрация по различным метаданным записей.

7. **Техническое примечание** — в текущей версии серверы развернуты на Gunicorn с Whitenoise для обслуживания статических файлов. Конфигурация оптимизирована для разработки и находится в отладочном режиме (DEBUG=True).

## Запуск системы через [Docker](https://www.docker.com/) (рекомендуется)

```bash
# Клонирование репозитория
git clone https://github.com/Alexman2505/Aeroflot_Hackathon.git
cd Aeroflot_Hackathon

# Настройка переменных окружения (неактуально, т.к. сейчас .env индексируется гитом!)
cp backend/.env.example backend/.env
cp photo_server/.env.example photo_server/.env

# Запуск всех сервисов
docker-compose up --build -d
```

## Настройка переменных окружения

В данный момент на этапе сдачи задания файлы .env индексируются гитом, поэтому проект запускается одной командой. Нет необходимости создавать и заполнять эти файлы вручную. В дальнейшем, после окончания хакатона, перед первым запуском необходимо создать и настроить файлы `.env` в папках `backend/` и `photo_server/` на примере тестовых файлов .env.example лежащих в проекте. Команды на создание через консоль написаны выше.

## Архитектура проекта

### [AeroToolKit Backend](http://aerotoolkit.sytes.net:8000/)

Основной сервис системы, разработанный на Django. Обрабатывает данные и управляет всей логикой. Основные функции:

- **Прием и обработка изображений** через REST API от фотосервера. Реализована интерактивная документация API ([swagger](http://aerotoolkit.sytes.net:8000/api/v1/swagger/), [redoc](http://aerotoolkit.sytes.net:8000/api/v1/redoc/))
- **Автоматическое распознавание инструментов** перед записью в базу с использованием ML-моделей YOLO
- **Хранение и учет результатов** в СУБД PostgreSQL, с системой мониторинга активности сотрудников
- **Веб-интерфейс** для визуализации результатов

### [Photo Server](http://aerotoolkit.sytes.net:8001/)

Тестовый сервис (клиент) имитирует работу систем видеонаблюдения. Основные функции:

- **Контроль доступа** — аутентификация сотрудников через секретные токены
- **Проверка данных** — валидация клиента на стороне сервера
- **Настройка параметров** — ВОЗМОЖНОСТЬ УКАЗАТЬ ОЖИДАЕМОЕ КОЛИЧЕСТВО ИНСТРУМЕНТОВ И ТРЕБУЕМЫЙ УРОВЕНЬ УВЕРЕННОСТИ РАСПОЗНАВАНИЯ ОТДЕЛЬНОГО ОБЪЕКТА ПЕРЕД ОТПРАВКОЙ ПАЧКИ ФОТОГРАФИЙ
- **Автоматическая отправка** — пакетная передача нескольких изображений за одну сессию на основной сервер AeroToolKit

### [Сетевая инфраструктура](https://www.docker.com/)

- **Изолированная Docker-сеть** — обеспечивает защищённое взаимодействие между сервисами AeroToolKit и Photo Server через внутренний сетевой мост
- **Автоматическая маршрутизация** — прозрачная связь между контейнерами с использованием доменных имён сервисов

## Технологический стек

### Backend & Infrastructure

- **Django Backend Architecture** - два независимых сервера с ORM, административной панелью и системой аутентификации
- **Server-Side Rendering** - генерация HTML на стороне сервера с Bootstrap стилизацией
- **REST API Development** - полнофункциональное API с токенной аутентификацией на Django REST Framework
- **Asynchronous Task Processing** - распределенная система фоновых асинхронных задач Celery для обработки изображений и YOLO-инференса
- **Message Queue & Broker** - Redis как брокер сообщений для управления очередями задач и межсервисного взаимодействия
- **Docker Containerization** - изолированная среда развертывания через Docker-контейнеры
- **Data Storage Infrastructure** - надежное хранение записей в изолированной в контейнере СУБД PostgreSQL
- **Performance Monitoring** - инструменты отладки с Django Debug Toolbar
- **Scalable Background Jobs** - параллельная обработка задач с возможностью поддержки повторных попыток и отказоустойчивостью

### Data Processing & Integration

- **Cross-Server Data Integration** - автоматизированный обмен данными между сервисами
- **Computer Vision Integration** - автоматическое распознавание объектов моделью YOLO перед сохранением
- **Quality Control System** - гибкая настройка параметров распознавания и валидации результатов
- **Automated API Documentation** - интерактивная документация через Swagger/Redoc

### User Management & Analytics

- **User Management System** - система управления сотрудниками с индивидуальной аутентификацией
- **User Activity Dashboard** - просмотр действий сотрудников и детализация их загрузок.

## Проект полностью построен на открытом программном обеспечении. Список используемых библиотек.

```
licenses aerotoolkit

 Name                   Version      License
 Django                 4.0.6        BSD License
 PyYAML                 6.0.3        MIT License
 amqp                   5.3.1        BSD License
 asgiref                3.9.1        BSD License
 async-timeout          5.0.1        Apache Software License
 billiard               4.2.2        BSD License
 celery                 5.3.4        BSD License
 certifi                2025.8.3     Mozilla Public License 2.0 (MPL 2.0)
 charset-normalizer     3.4.3        MIT
 click                  8.3.0        UNKNOWN
 click-didyoumean       0.3.1        MIT License
 click-plugins          1.1.1.2      BSD License
 click-repl             0.3.0        MIT
 colorama               0.4.6        BSD License
 django-celery-results  2.5.1        BSD License
 djangorestframework    3.13.0       BSD License
 drf-yasg               1.21.10      BSD License
 gunicorn               23.0.0       MIT License
 idna                   3.10         BSD License
 inflection             0.5.1        MIT License
 kombu                  5.5.4        BSD License
 packaging              25.0         Apache Software License; BSD License
 pillow                 11.3.0       UNKNOWN
 prompt_toolkit         3.0.52       BSD License
 python-dateutil        2.9.0.post0  Apache Software License; BSD License
 python-dotenv          1.1.1        BSD License
 pytz                   2025.2       MIT License
 redis                  5.0.1        MIT License
 requests               2.32.5       Apache Software License
 six                    1.17.0       MIT License
 sqlparse               0.5.3        BSD License
 typing_extensions      4.15.0       UNKNOWN
 tzdata                 2025.2       Apache Software License
 uritemplate            4.2.0        BSD 3-Clause OR Apache-2.0
 urllib3                2.5.0        UNKNOWN
 vine                   5.1.0        BSD License
 whitenoise             6.6.0        MIT License

licenses photo_service
 Django                 4.0.6        BSD License
 PyYAML                 6.0.3        MIT License
 amqp                   5.3.1        BSD License
 asgiref                3.9.1        BSD License
 async-timeout          5.0.1        Apache Software License
 billiard               4.2.2        BSD License
 celery                 5.3.4        BSD License
 certifi                2025.8.3     Mozilla Public License 2.0 (MPL 2.0)
 charset-normalizer     3.4.3        MIT
 click                  8.3.0        UNKNOWN
 click-didyoumean       0.3.1        MIT License
 click-plugins          1.1.1.2      BSD License
 click-repl             0.3.0        MIT
 colorama               0.4.6        BSD License
 django-celery-results  2.5.1        BSD License
 djangorestframework    3.13.0       BSD License
 drf-yasg               1.21.10      BSD License
 gunicorn               23.0.0       MIT License
 idna                   3.10         BSD License
 inflection             0.5.1        MIT License
 kombu                  5.5.4        BSD License
 packaging              25.0         Apache Software License; BSD License
 pillow                 11.3.0       UNKNOWN
 prompt_toolkit         3.0.52       BSD License
 python-dateutil        2.9.0.post0  Apache Software License; BSD License
 python-dotenv          1.1.1        BSD License
 pytz                   2025.2       MIT License
 redis                  5.0.1        MIT License
 requests               2.32.5       Apache Software License
 six                    1.17.0       MIT License
 sqlparse               0.5.3        BSD License
 typing_extensions      4.15.0       UNKNOWN
 tzdata                 2025.2       Apache Software License
 uritemplate            4.2.0        BSD 3-Clause OR Apache-2.0
 urllib3                2.5.0        UNKNOWN
 vine                   5.1.0        BSD License
 whitenoise             6.6.0        MIT License
```

## Структура проекта

```bash
Aeroflot_Hackathon/
├── backend/                          # Основной сервис AeroToolKit
│   ├── AeroToolKit/                  # Корневая папка проекта Django
│   │   ├── AeroToolKit/              # Папка с настройками проекта бэкенда
│   │   │   ├── settings.py           # Настройки Django
│   │   │   ├── urls.py               # Маршрутизатор ссылок
│   │   │   ├── celery.py             # Загрузка конфигурации Celery
│   │   │   └── wsgi.py               # WSGI конфигурация Django проекта (Web Server Gateway Interface)
│   │   ├── instruments/              # Приложение для работы с инструментами
│   │   │   ├── models.py             # Модели Instrument
│   │   │   ├── views.py              # Веб-представления
│   │   │   └── urls.py               # Маршрутизатор ссылок
│   │   ├── templates/                # HTML шаблоны
│   │   ├── api/                      # REST API приложение
│   │   │   ├── views.py              # ViewSets для инструментов
│   │   │   ├── serializers.py        # Сериализаторы
│   │   │   ├── urls.py               # Маршрутизатор ссылок
│   │   │   └── yolo_utils.py         # Утилиты для работы с YOLO моделью
│   │   │   └── tasks.py              # Реализация работы очереди
│   │   ├── users/                    # Приложение пользователей
│   │   │   ├── models.py             # Модели пользователей
│   │   │   └── urls.py               # Маршрутизатор ссылок
│   │   ├── manage.py                 # Главный исполнительный файл
│   │   ├── requirements.txt          # Список используемых библиотек
│   │   └── .env                      # Переменные окружения
├── photo_server/                     # Сервис загрузки изображений
│   ├── image_service/                # Корневая папка проекта Django
│   │   ├── settings.py               # Настройки Django
│   │   ├── celery.py                 # Загрузка конфигурации Celery
│   │   ├── urls.py                   # Маршрутизатор ссылок
│   │   └── wsgi.py                   # WSGI конфигурация Django проекта (Web Server Gateway Interface)
│   ├── api/                          # API приложение
│   │   ├── views.py                  # Логика загрузки и отправки
│   │   ├── urls.py                   # Маршрутизатор ссылок
│   │   └── tasks.py                  # Реализация работы очереди
│   ├── templates/                    # HTML шаблоны
│   ├── manage.py                     # Главный исполнительный файл
│   ├── requirements.txt              # Список используемых библиотек.
│   └── .env                          # Переменные окружения
├── dev_ml/                           # Модуль машинного обучения
│   ├── datasets/                     # Датасеты для обучения
│   │   └── data.yaml
│   ├── models/                       # Обученные модели
│   │   └── yolo_best.pt
│   └── train_yolo.py                 # Обучение YOLO модели
├── docker-compose.yml                # Конфигурация Docker
├── .gitignore                        # Игнорируемые гитхабом файлы при публикации.
└── README.md
```

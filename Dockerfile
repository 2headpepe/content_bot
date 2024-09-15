# Используем базовый образ с последней версией Python
FROM python:3.9

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл зависимостей в контейнер
COPY requirements.txt ./

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем необходимые браузеры для Playwright
RUN python -m playwright install
RUN python -m playwright install-deps

# Копируем остальные файлы в контейнер
COPY . .

# Начинаем основной скрипт
CMD ["python", "main.py"]
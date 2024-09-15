# Используем базовый образ с последней версией Python
FROM python:3.9

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл зависимостей в контейнер
COPY requirements.txt ./

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем необходимые системные зависимости для Playwright
RUN apt-get update && apt-get install -y \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libpango-1.0-0 \
    libxcomposite1 \
    libxrandr2 \
    libgtk-3-0 \
    libasound2 \
    libxshmfence1 \
    xvfb && \
    python -m playwright install-deps

# Устанавливаем браузеры Playwright
RUN python -m playwright install

# Копируем остальные файлы в контейнер
COPY . .

# Запускаем приложение с использованием Xvfb
CMD ["xvfb-run", "--auto-servernum", "--", "python", "main.py"]
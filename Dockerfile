FROM python:3.9-slim

# Устанавливаем системные зависимости для OpenCV и видео
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей и устанавливаем Python-библиотеки
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения и шаблоны
COPY app.py .
COPY analyze_video.py .
COPY templates/ ./templates/
COPY static/ ./static/

# Создаем папки для загрузок и обработки видео
RUN mkdir -p static/uploads static/processed static/removed_videos

# Открываем порт Flask
EXPOSE 5000

# Запускаем приложение
CMD ["python", "app.py"]

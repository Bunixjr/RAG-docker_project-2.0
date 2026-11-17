# Используем официальный образ Python (версия 3.12, как у тебя)
FROM python:3.12-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Сначала копируем только requirements.txt, чтобы Docker закэшировал установку библиотек
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
# (флаг --no-cache-dir нужен, чтобы не засорять контейнер кэшем)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем все остальные файлы проекта (папку src, папку data и т.д.)
COPY . .

# Команда, которая запустится при старте контейнера
CMD ["python", "src/generate.py"]

FROM python:3.12-slim

WORKDIR /app
#Создание папки app
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "src/generate.py"]
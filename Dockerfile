FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Сначала зависимости: слой переиспользуется, пока requirements.txt не изменился.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем код, миграции и конфиг Alembic.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

# 0.0.0.0 обязателен: иначе Uvicorn будет слушать только внутри контейнера.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

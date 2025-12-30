FROM python:3.11-slim

WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код приложения
COPY . .

# Запускаем бота
CMD ["python", "bot.py"]


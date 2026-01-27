# Используем конкретную версию 3.12
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Запрещаем Python писать файлы .pyc на диск и включаем буферизацию логов
# (Это полезно, чтобы ты видел логи бота в панели Railway сразу)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

CMD ["python", "main.py"]
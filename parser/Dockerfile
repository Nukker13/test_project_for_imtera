FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-browsers

WORKDIR /app

# Ставим зависимости и браузер отдельным слоем от кода — пересборка при правке
# парсера не тянет за собой повторную выкачку браузера (это самый долгий шаг).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Под linux/arm64 (Apple Silicon) Google Chrome не существует, поэтому ставим
# chromium из сборки Patchright. На amd64 при желании можно догрузить реальный
# Chrome и включить его через PATCHRIGHT_CHANNEL=chrome — см. README.
RUN patchright install --with-deps chromium

COPY . .

EXPOSE 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]

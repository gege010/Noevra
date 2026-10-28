# Stage 1 & 2: No GTK/WeasyPrint deps needed — fpdf2 is pure Python
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY frontend/ ./frontend/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 noevra && mkdir -p /app/data/reports && chown -R noevra:noevra /app/data
USER noevra

HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/live', timeout=3)"
EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
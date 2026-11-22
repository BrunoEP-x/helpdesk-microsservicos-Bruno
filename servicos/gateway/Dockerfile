# Contexto de build: raiz do repositório (para copiar a biblioteca comum)
FROM python:3.12-slim

RUN useradd --create-home --uid 10001 helpdesk

WORKDIR /srv
COPY servicos/gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY comum/helpdesk_comum ./helpdesk_comum
COPY servicos/gateway/app ./app

USER helpdesk
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

# Contexto de build: raiz do repositório (para copiar a biblioteca comum)
FROM python:3.15-slim

# Não roda como root dentro do contêiner
RUN useradd --create-home --uid 10001 helpdesk && mkdir /dados && chown helpdesk /dados

WORKDIR /srv
COPY servicos/assistente/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY comum/helpdesk_comum ./helpdesk_comum
COPY servicos/assistente/app ./app

USER helpdesk
ENV DATABASE_URL=sqlite:////dados/assistente.db \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

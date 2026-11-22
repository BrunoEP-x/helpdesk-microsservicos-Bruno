# Contexto de build: raiz do repositório (para copiar a biblioteca comum)
FROM python:3.12-slim

# Não roda como root dentro do contêiner
RUN useradd --create-home --uid 10001 helpdesk && mkdir /dados && chown helpdesk /dados

WORKDIR /srv
COPY servicos/usuarios/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY comum/helpdesk_comum ./helpdesk_comum
COPY servicos/usuarios/app ./app

USER helpdesk
ENV DATABASE_URL=sqlite:////dados/usuarios.db \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
EXPOSE 8000
# --proxy-headers: o endereço real do cliente vem do gateway (X-Forwarded-For), usado no limite de tentativas.
# Só o gateway alcança este serviço (rede interna do Docker), por isso aceitar o cabeçalho é seguro.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

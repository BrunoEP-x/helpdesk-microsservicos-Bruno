import os

from helpdesk_comum.config import url_servico

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chamados.db")
DADOS_EXEMPLO = os.getenv("DADOS_EXEMPLO", "1") == "1"
USUARIOS_URL = url_servico("usuarios", "http://localhost:8001")
INVENTARIO_URL = url_servico("inventario", "http://localhost:8002")
# Fila de eventos. Sem REDIS_URL, os eventos ficam guardados na tabela de saída (outbox)
# e são publicados quando a fila estiver disponível.
REDIS_URL = os.getenv("REDIS_URL", "")
INTERVALO_PUBLICACAO = float(os.getenv("INTERVALO_PUBLICACAO", "2"))
INTERVALO_VERIFICACAO_SLA = float(os.getenv("INTERVALO_VERIFICACAO_SLA", "60"))
TAREFAS_ATIVAS = os.getenv("TAREFAS_ATIVAS", "1") == "1"

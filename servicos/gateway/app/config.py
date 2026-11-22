"""Tabela de rotas do gateway: prefixo da URL -> serviço interno."""
import os

from helpdesk_comum.config import url_servico

SERVICOS = {
    "usuarios": url_servico("usuarios", "http://localhost:8001"),
    "inventario": url_servico("inventario", "http://localhost:8002"),
    "chamados": url_servico("chamados", "http://localhost:8003"),
    "notificacoes": url_servico("notificacoes", "http://localhost:8004"),
    "assistente": url_servico("assistente", "http://localhost:8005"),
}

ROTAS = {
    "auth": "usuarios",
    "usuarios": "usuarios",
    "ativos": "inventario",
    "chamados": "chamados",
    "notificacoes": "notificacoes",
    "assistente": "assistente",
}

NOMES = {"usuarios": "Usuários", "inventario": "Inventário", "chamados": "Chamados",
         "notificacoes": "Notificações", "assistente": "Assistente"}

TIMEOUT = float(os.getenv("TIMEOUT_GATEWAY", "10"))
TIMEOUT_SAUDE = float(os.getenv("TIMEOUT_SAUDE", "1.5"))

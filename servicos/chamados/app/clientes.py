"""Conversa com os serviços de Usuários e Inventário pela rede (HTTP com timeout).

São dependências do FastAPI: nos testes, trocamos por serviços simulados.
"""
from app.config import INVENTARIO_URL, USUARIOS_URL
from helpdesk_comum.clientes import ClienteServico


def cliente_usuarios() -> ClienteServico:
    return ClienteServico("Usuários", USUARIOS_URL)


def cliente_inventario() -> ClienteServico:
    return ClienteServico("Inventário", INVENTARIO_URL)

"""Conversa com o serviço de Usuários pela rede (HTTP com timeout)."""
from app.config import USUARIOS_URL
from helpdesk_comum.clientes import ClienteServico


def cliente_usuarios() -> ClienteServico:
    """Dependência do FastAPI: nos testes, é trocada por um serviço simulado."""
    return ClienteServico("Usuários", USUARIOS_URL)

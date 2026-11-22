import os

from helpdesk_comum.config import url_servico

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./inventario.db")
DADOS_EXEMPLO = os.getenv("DADOS_EXEMPLO", "1") == "1"
USUARIOS_URL = url_servico("usuarios", "http://localhost:8001")

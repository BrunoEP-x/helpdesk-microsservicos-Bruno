import os

from helpdesk_comum.config import url_servico

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./notificacoes.db")
REDIS_URL = os.getenv("REDIS_URL", "")
USUARIOS_URL = url_servico("usuarios", "http://localhost:8001")
CONSUMIDOR_ATIVO = os.getenv("CONSUMIDOR_ATIVO", "1") == "1"
NOME_CONSUMIDOR = os.getenv("HOSTNAME", "notificacoes-1")

# E-mail (opcional). Sem SMTP_HOST, os avisos ficam só na tela.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORTA = int(os.getenv("SMTP_PORTA", "587"))
SMTP_USUARIO = os.getenv("SMTP_USUARIO", "")
SMTP_SENHA = os.getenv("SMTP_SENHA", "")
SMTP_REMETENTE = os.getenv("SMTP_REMETENTE", "helpdesk@empresa.com")

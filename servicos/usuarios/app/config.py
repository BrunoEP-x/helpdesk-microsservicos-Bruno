import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./usuarios.db")
DADOS_EXEMPLO = os.getenv("DADOS_EXEMPLO", "1") == "1"
SENHA_EXEMPLO = os.getenv("SENHA_EXEMPLO", "Helpdesk2026")

# Proteção contra tentativas de adivinhar senhas
LOGIN_MAX_FALHAS = int(os.getenv("LOGIN_MAX_FALHAS", "5"))
LOGIN_JANELA_SEGUNDOS = int(os.getenv("LOGIN_JANELA_SEGUNDOS", "300"))
# Com REDIS_URL, o limite de tentativas fica no Redis e vale para várias instâncias do serviço
REDIS_URL = os.getenv("REDIS_URL", "")

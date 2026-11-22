"""Configurações comuns lidas das variáveis de ambiente.

O segredo do JWT é o único valor que precisa ser igual em todos os serviços.
Ordem de leitura:
1. variável JWT_SEGREDO (vinda do .env);
2. arquivo indicado em JWT_SEGREDO_ARQUIVO (gerado pelo contêiner "segredos"
   do docker compose, para o sistema subir sem ajustes manuais).
O segredo nunca fica no código.
"""
import os
from pathlib import Path

JWT_ALGORITMO = "HS256"
JWT_EMISSOR = "helpdesk-pro"
TOKEN_MINUTOS = int(os.getenv("TOKEN_MINUTOS", "60"))
TAMANHO_MAXIMO_REQUISICAO = 64 * 1024
DOCS_ATIVA = os.getenv("DOCS", "1") == "1"
TIMEOUT_HTTP = float(os.getenv("TIMEOUT_HTTP", "3"))


class SegredoAusente(RuntimeError):
    pass


def jwt_segredo() -> str:
    segredo = os.getenv("JWT_SEGREDO", "").strip()
    if not segredo:
        arquivo = os.getenv("JWT_SEGREDO_ARQUIVO", "").strip()
        if arquivo and Path(arquivo).is_file():
            segredo = Path(arquivo).read_text().strip()
    if len(segredo) < 32:
        raise SegredoAusente(
            "JWT_SEGREDO ausente ou com menos de 32 caracteres. Defina no .env "
            "ou aponte JWT_SEGREDO_ARQUIVO para um arquivo com o segredo."
        )
    return segredo


def url_servico(nome: str, padrao: str) -> str:
    """Endereço de outro serviço. No Docker, os serviços se chamam pelo nome."""
    return os.getenv(f"{nome.upper()}_URL", padrao).rstrip("/")

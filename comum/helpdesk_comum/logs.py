"""Logs em JSON, uma linha por evento, com o nome do serviço e o X-Request-ID.

Formato fácil de filtrar com `docker compose logs` ou de enviar a uma
ferramenta de observabilidade.
"""
import json
import logging
import os
from datetime import datetime, timezone


class FormatoJson(logging.Formatter):
    def __init__(self, servico: str):
        super().__init__()
        self.servico = servico

    def format(self, registro: logging.LogRecord) -> str:
        from helpdesk_comum.http import id_requisicao

        dados = {
            "hora": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "servico": self.servico,
            "nivel": registro.levelname,
            "origem": registro.name,
            "mensagem": registro.getMessage(),
            "requisicao": id_requisicao.get(),
        }
        if registro.exc_info:
            dados["erro"] = self.formatException(registro.exc_info)
        return json.dumps(dados, ensure_ascii=False)


def configurar(servico: str) -> None:
    raiz = logging.getLogger("helpdesk")
    if getattr(raiz, "_configurado", False):
        return
    saida = logging.StreamHandler()
    saida.setFormatter(FormatoJson(servico))
    raiz.addHandler(saida)
    raiz.setLevel(os.getenv("NIVEL_LOG", "INFO"))
    raiz.propagate = False
    raiz._configurado = True  # type: ignore[attr-defined]

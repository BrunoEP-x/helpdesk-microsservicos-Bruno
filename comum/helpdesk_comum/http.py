"""Middleware HTTP comum: limite de tamanho, cabeçalhos de segurança,
identificador de requisição (X-Request-ID) e log de acesso.

O X-Request-ID nasce no gateway e é repassado a cada serviço chamado,
então dá para seguir uma mesma ação pelos logs de todos os contêineres.
"""
import logging
import re
import time
import uuid
from contextvars import ContextVar

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from helpdesk_comum.config import TAMANHO_MAXIMO_REQUISICAO

id_requisicao: ContextVar[str] = ContextVar("id_requisicao", default="-")
log_acesso = logging.getLogger("helpdesk.acesso")

_ID_VALIDO = re.compile(r"^[A-Za-z0-9-]{8,64}$")

# A tela só carrega arquivos do próprio servidor (bloqueia scripts injetados)
CSP_TELA = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)
# A documentação (Swagger) carrega arquivos de um CDN
CSP_DOCS = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; "
    "frame-ancestors 'none'; base-uri 'none'"
)


class CabecalhosDeSeguranca(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        recebido = request.headers.get("x-request-id", "")
        rid = recebido if _ID_VALIDO.match(recebido) else uuid.uuid4().hex
        id_requisicao.set(rid)
        inicio = time.perf_counter()

        tamanho = request.headers.get("content-length")
        if tamanho and (not tamanho.isdigit() or int(tamanho) > TAMANHO_MAXIMO_REQUISICAO):
            return JSONResponse(status_code=413, content={"detail": "Requisição grande demais."})

        resposta = await call_next(request)
        documentacao = request.url.path in ("/docs", "/redoc", "/openapi.json")
        resposta.headers["Content-Security-Policy"] = CSP_DOCS if documentacao else CSP_TELA
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "no-referrer"
        resposta.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        resposta.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        resposta.headers["X-Request-ID"] = rid
        if request.headers.get("authorization"):
            resposta.headers["Cache-Control"] = "no-store"

        if request.url.path != "/saude":
            log_acesso.info("%s %s -> %s (%.1f ms)", request.method, request.url.path, resposta.status_code,
                            (time.perf_counter() - inicio) * 1000)
        return resposta

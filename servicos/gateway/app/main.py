"""API Gateway do HelpDesk Pro.

- Único contêiner com porta publicada (127.0.0.1:8000).
- Encaminha /auth e /usuarios para Usuários, /ativos para Inventário,
  /chamados para Chamados, /notificacoes para Notificações e /assistente para o Assistente.
- Repassa o token (Authorization), cria o X-Request-ID e informa o IP real (X-Forwarded-For).
- Se um serviço cair, só as rotas dele respondem 503; o resto continua funcionando.
- GET /saude mostra quais serviços estão no ar.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app import config
from helpdesk_comum import logs
from helpdesk_comum.erros import registrar_tratadores
from helpdesk_comum.http import CabecalhosDeSeguranca, id_requisicao

WEB = Path(__file__).parent / "web"
log = logging.getLogger("helpdesk.gateway")
logs.configurar("gateway")

# Só estes cabeçalhos seguem para os serviços (o resto é descartado)
CABECALHOS_ENTRADA = ("authorization", "content-type", "accept", "accept-language")
CABECALHOS_SAIDA = ("content-type", "content-disposition", "www-authenticate", "retry-after")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    if not hasattr(app.state, "http"):
        app.state.http = httpx.AsyncClient(timeout=config.TIMEOUT)
    yield
    await app.state.http.aclose()


app = FastAPI(title="HelpDesk Pro · API Gateway", version="3.0.0", lifespan=ciclo_de_vida,
              docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CabecalhosDeSeguranca)
registrar_tratadores(app)
app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/saude", tags=["Saúde"])
async def saude():
    """Consulta a rota /saude de cada serviço ao mesmo tempo (com tempo limite curto)."""
    async def checar(nome: str, url: str):
        inicio = time.perf_counter()
        try:
            r = await app.state.http.get(f"{url}/saude", timeout=config.TIMEOUT_SAUDE)
            ok = r.status_code == 200
            extra = r.json() if ok else {}
        except (httpx.HTTPError, ValueError):
            ok, extra = False, {}
        return nome, {"status": "ok" if ok else "fora do ar", "latencia_ms": round((time.perf_counter() - inicio) * 1000),
                      **({"fila": extra["fila"]} if "fila" in extra else {})}

    resultados = dict(await asyncio.gather(*(checar(n, u) for n, u in config.SERVICOS.items())))
    todos_ok = all(r["status"] == "ok" for r in resultados.values())
    return {"status": "ok" if todos_ok else "degradado", "gateway": "ok", "servicos": resultados}


@app.get("/", include_in_schema=False)
def tela_inicial():
    return FileResponse(WEB / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(WEB / "favicon.svg", media_type="image/svg+xml")


@app.api_route("/{caminho:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
async def encaminhar(caminho: str, request: Request):
    servico = config.ROTAS.get(caminho.split("/", 1)[0])
    if servico is None:
        return JSONResponse(status_code=404, content={"detail": "Rota não encontrada."})

    cabecalhos = {k: v for k, v in request.headers.items() if k.lower() in CABECALHOS_ENTRADA}
    cabecalhos["X-Request-ID"] = id_requisicao.get()
    cabecalhos["X-Forwarded-For"] = request.client.host if request.client else "-"
    url = f"{config.SERVICOS[servico]}/{caminho}"
    try:
        resposta = await app.state.http.request(request.method, url, params=request.query_params,
                                                content=await request.body(), headers=cabecalhos)
    except httpx.TimeoutException:
        log.warning("tempo esgotado no serviço %s (%s)", servico, caminho)
        return JSONResponse(status_code=503, content={
            "detail": f"O serviço de {config.NOMES[servico]} não respondeu a tempo. Tente novamente em instantes."})
    except httpx.HTTPError:
        log.warning("serviço %s fora do ar (%s)", servico, caminho)
        return JSONResponse(status_code=503, content={
            "detail": f"O serviço de {config.NOMES[servico]} está indisponível no momento."})

    saida = {k: v for k, v in resposta.headers.items() if k.lower() in CABECALHOS_SAIDA}
    return Response(content=resposta.content, status_code=resposta.status_code, headers=saida)

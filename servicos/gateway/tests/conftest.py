import os

os.environ["JWT_SEGREDO"] = "segredo-de-teste-com-mais-de-32-caracteres-ok"

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

FORA_DO_AR = {"inventario"}


def servicos_simulados(request: httpx.Request) -> httpx.Response:
    """Responde como se fosse cada serviço; o inventário está "fora do ar"."""
    servico = request.url.host
    if servico in FORA_DO_AR:
        raise httpx.ConnectError("conexão recusada", request=request)
    if request.url.path == "/saude":
        return httpx.Response(200, json={"status": "ok", "servico": servico})
    return httpx.Response(200, json={
        "servico": servico, "caminho": request.url.path, "consulta": str(request.url.query, "utf-8"),
        "metodo": request.method, "corpo": request.content.decode() or None,
        "authorization": request.headers.get("authorization"), "request_id": request.headers.get("x-request-id"),
        "cookie": request.headers.get("cookie"), "encaminhado_para": request.headers.get("x-forwarded-for"),
    }, headers={"X-Interno": "nao-deve-vazar"})


@pytest.fixture
def cliente(monkeypatch):
    from app import config
    monkeypatch.setattr(config, "SERVICOS", {n: f"http://{n}" for n in config.SERVICOS})
    app.state.http = httpx.AsyncClient(transport=httpx.MockTransport(servicos_simulados))
    with TestClient(app) as c:
        yield c
    del app.state.http

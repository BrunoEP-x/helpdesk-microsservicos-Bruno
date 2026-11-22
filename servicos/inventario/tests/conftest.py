import os

os.environ["JWT_SEGREDO"] = "segredo-de-teste-com-mais-de-32-caracteres-ok"
os.environ["DADOS_EXEMPLO"] = "0"
os.environ["DATABASE_URL"] = "sqlite://"

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.banco import banco  # noqa: E402
from app.clientes import cliente_usuarios  # noqa: E402
from app.main import app  # noqa: E402
from helpdesk_comum import tokens  # noqa: E402
from helpdesk_comum.clientes import ClienteServico  # noqa: E402

# Usuários que o "serviço de Usuários" simulado conhece
USUARIOS = {1: ("Admin", "admin"), 2: ("Ana", "solicitante"), 3: ("Bia", "solicitante"), 4: ("Carla", "tecnico"),
            5: ("Ex-funcionário", "solicitante")}


def usuarios_simulado(request: httpx.Request) -> httpx.Response:
    assert request.headers["authorization"].startswith("Bearer ")  # o token foi repassado
    uid = int(request.url.path.rsplit("/", 1)[1])
    if uid not in USUARIOS:
        return httpx.Response(404, json={"detail": f"Usuário {uid} não encontrado."})
    nome, perfil = USUARIOS[uid]
    return httpx.Response(200, json={"id": uid, "nome": nome, "perfil": perfil, "setor": None, "ativo": uid != 5})


@pytest.fixture
def cliente():
    banco.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    banco.Sessao = sessionmaker(bind=banco.engine, autoflush=False, expire_on_commit=False)
    app.dependency_overrides[cliente_usuarios] = lambda: ClienteServico(
        "Usuários", "http://usuarios", transporte=httpx.MockTransport(usuarios_simulado))
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def contas():
    def cab(uid):
        nome, perfil = USUARIOS[uid]
        return {"Authorization": f"Bearer {tokens.criar(uid, perfil, nome)[0]}"}
    return {"admin": cab(1), "ana": cab(2), "bia": cab(3), "carla": cab(4)}

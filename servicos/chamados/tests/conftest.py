import os

os.environ["JWT_SEGREDO"] = "segredo-de-teste-com-mais-de-32-caracteres-ok"
os.environ["DADOS_EXEMPLO"] = "0"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["TAREFAS_ATIVAS"] = "0"
os.environ.pop("REDIS_URL", None)

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.banco import banco  # noqa: E402
from app.clientes import cliente_inventario, cliente_usuarios  # noqa: E402
from app.main import app  # noqa: E402
from app.modelos import EventoPendente  # noqa: E402
from helpdesk_comum import tokens  # noqa: E402
from helpdesk_comum.clientes import ClienteServico  # noqa: E402

USUARIOS = {1: ("Admin", "admin"), 2: ("Ana", "solicitante"), 3: ("Bia", "solicitante"), 4: ("Carla", "tecnico")}
ATIVOS = {1: {"id": 1, "patrimonio": "PAT-1", "tipo": "computador", "descricao": "Desktop", "setor": "TI"},
          2: {"id": 2, "patrimonio": "PAT-2", "tipo": "rede", "descricao": "Switch", "setor": "TI"}}


def _simulado(registros, montar):
    def responder(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"].startswith("Bearer ")  # o token do usuário foi repassado
        rid = int(request.url.path.rsplit("/", 1)[1])
        if rid not in registros:
            return httpx.Response(404, json={"detail": f"Registro {rid} não encontrado."})
        return httpx.Response(200, json=montar(rid))
    return httpx.MockTransport(responder)


usuarios_ok = lambda: ClienteServico("Usuários", "http://usuarios", transporte=_simulado(
    USUARIOS, lambda i: {"id": i, "nome": USUARIOS[i][0], "perfil": USUARIOS[i][1], "ativo": True, "setor": None}))
inventario_ok = lambda: ClienteServico("Inventário", "http://inventario", transporte=_simulado(ATIVOS, ATIVOS.get))
fora_do_ar = lambda nome: (lambda: ClienteServico(nome, "http://127.0.0.1:9", timeout=0.5))


@pytest.fixture
def sessao():
    banco.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    banco.Sessao = sessionmaker(bind=banco.engine, autoflush=False, expire_on_commit=False)
    return banco.Sessao


@pytest.fixture
def cliente(sessao):
    app.dependency_overrides[cliente_usuarios] = usuarios_ok
    app.dependency_overrides[cliente_inventario] = inventario_ok
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def contas():
    def conta(uid):
        nome, perfil = USUARIOS[uid]
        return {"headers": {"Authorization": f"Bearer {tokens.criar(uid, perfil, nome)[0]}"}, "id": uid}
    return {"admin": conta(1), "ana": conta(2), "bia": conta(3), "carla": conta(4)}


@pytest.fixture
def ativo():
    return ATIVOS[1]


@pytest.fixture
def eventos(sessao):
    """Lê os eventos gravados na tabela de saída (outbox)."""
    def ler(tipo=None):
        with sessao() as db:
            todos = [__import__("json").loads(e.conteudo) for e in db.scalars(select(EventoPendente).order_by(EventoPendente.criado_em))]
        return [e for e in todos if tipo is None or e["tipo"] == tipo]
    return ler

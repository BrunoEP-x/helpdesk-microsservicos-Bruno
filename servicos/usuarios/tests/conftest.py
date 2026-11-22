import os

os.environ["JWT_SEGREDO"] = "segredo-de-teste-com-mais-de-32-caracteres-ok"
os.environ["DADOS_EXEMPLO"] = "0"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.pop("REDIS_URL", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import servico  # noqa: E402
from app.banco import banco  # noqa: E402
from app.esquemas import UsuarioCriar  # noqa: E402
from app.limite import limite  # noqa: E402
from app.main import app  # noqa: E402

SENHA = "Senha123"


@pytest.fixture
def sessao():
    """Banco novo, em memória, para cada teste (as migrações rodam ao iniciar o app)."""
    limite.limpar_tudo()
    banco.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    banco.Sessao = sessionmaker(bind=banco.engine, autoflush=False, expire_on_commit=False)
    return banco.Sessao


@pytest.fixture
def cliente(sessao):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def contas(sessao, cliente):
    """Cria um admin, dois solicitantes e um técnico, e devolve o cabeçalho de login de cada um."""
    with sessao() as db:
        for nome, email, perfil in [("Admin", "admin@x.com", "admin"), ("Ana", "ana@x.com", "solicitante"),
                                    ("Bia", "bia@x.com", "solicitante"), ("Carla", "carla@x.com", "tecnico")]:
            servico.criar(db, UsuarioCriar(nome=nome, email=email, perfil=perfil, senha=SENHA))
    resultado = {}
    for apelido in ("admin", "ana", "bia", "carla"):
        r = cliente.post("/auth/login", json={"email": f"{apelido}@x.com", "senha": SENHA}).json()
        resultado[apelido] = {"headers": {"Authorization": f"Bearer {r['access_token']}"}, "id": r["usuario"]["id"]}
    return resultado

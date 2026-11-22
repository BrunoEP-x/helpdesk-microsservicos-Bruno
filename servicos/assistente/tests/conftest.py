import os

os.environ["JWT_SEGREDO"] = "segredo-de-teste-com-mais-de-32-caracteres-ok"
os.environ["DATABASE_URL"] = "sqlite://"


import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.banco import MIGRACOES, banco  # noqa: E402
from helpdesk_comum.banco import migrar  # noqa: E402
from app.main import app  # noqa: E402
from helpdesk_comum import tokens  # noqa: E402


@pytest.fixture
def sessao():
    banco.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    banco.Sessao = sessionmaker(bind=banco.engine, autoflush=False, expire_on_commit=False)
    migrar(banco.engine, MIGRACOES)
    return banco.Sessao


@pytest.fixture
def cliente(sessao):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def cab():
    return lambda uid, perfil="solicitante": {"Authorization": f"Bearer {tokens.criar(uid, perfil, f'U{uid}')[0]}"}

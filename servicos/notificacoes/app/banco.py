"""Banco exclusivo do serviço de Notificações."""
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL
from helpdesk_comum.banco import Banco, Migracao

banco = Banco(DATABASE_URL)


class Base(DeclarativeBase):
    pass


def get_db():
    yield from banco.get_db()


def _v1(conexao):
    from app import modelos  # noqa: F401
    Base.metadata.create_all(conexao)


MIGRACOES = [Migracao(1, "estrutura inicial de notificações", _v1)]

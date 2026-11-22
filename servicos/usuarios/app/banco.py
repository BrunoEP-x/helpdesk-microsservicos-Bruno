"""Banco exclusivo do serviço de Usuários."""
from sqlalchemy.orm import DeclarativeBase

from helpdesk_comum.banco import Banco, Migracao
from app.config import DATABASE_URL

banco = Banco(DATABASE_URL)


class Base(DeclarativeBase):
    pass


def get_db():
    yield from banco.get_db()


def _v1(conexao):
    from app import modelos  # noqa: F401  (registra as tabelas)
    Base.metadata.create_all(conexao)


MIGRACOES = [Migracao(1, "estrutura inicial de usuários", _v1)]

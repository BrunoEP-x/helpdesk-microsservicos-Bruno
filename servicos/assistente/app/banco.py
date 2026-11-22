"""Banco exclusivo do serviço Assistente."""
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


def _v2(conexao):
    """Base de conhecimento inicial (conteúdo de suporte, não dados de exemplo)."""
    from app.base_inicial import ARTIGOS
    from app.modelos import Artigo
    for artigo in ARTIGOS:
        conexao.execute(Artigo.__table__.insert().values(**artigo, ativo=True, consultas=0, util_sim=0, util_nao=0))


MIGRACOES = [Migracao(1, "estrutura inicial do assistente", _v1), Migracao(2, "base de conhecimento inicial", _v2)]

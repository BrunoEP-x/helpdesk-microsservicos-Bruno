"""Banco exclusivo do serviço de Chamados."""
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
    """Prazos padrão de SLA (o administrador pode alterar depois pela tela)."""
    from app.modelos import ConfiguracaoSla
    from app.sla import PADRAO
    for prioridade, (horas, alerta) in PADRAO.items():
        conexao.execute(ConfiguracaoSla.__table__.insert().values(
            prioridade=prioridade, horas=horas, alerta_percentual=alerta))


MIGRACOES = [
    Migracao(1, "estrutura inicial de chamados", _v1),
    Migracao(2, "prazos padrão de SLA", _v2),
]

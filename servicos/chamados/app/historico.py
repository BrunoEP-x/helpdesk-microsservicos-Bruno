"""Registro de auditoria (histórico) dos chamados."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos import Historico
from helpdesk_comum.banco import agora
from helpdesk_comum.tokens import UsuarioToken


def registrar(db: Session, chamado_id: int, acao: str, quem: UsuarioToken | None = None, campo: str | None = None,
              antes: object = None, depois: object = None, detalhe: str | None = None) -> None:
    """Adiciona uma linha ao histórico na transação atual (quem chama faz o commit)."""
    db.add(Historico(
        chamado_id=chamado_id, acao=acao, campo=campo,
        valor_anterior=None if antes is None else str(antes)[:240],
        valor_novo=None if depois is None else str(depois)[:240],
        detalhe=detalhe[:500] if detalhe else None,
        autor_id=quem.id if quem else None, autor_nome=quem.nome if quem else "Sistema", criado_em=agora(),
    ))


def listar(db: Session, chamado_id: int) -> list[Historico]:
    return list(db.scalars(select(Historico).where(Historico.chamado_id == chamado_id).order_by(Historico.id)))

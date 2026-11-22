"""Consultas do serviço de Chamados (uso interno)."""
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.modelos import ABERTOS, Chamado


def buscar_por_id(db: Session, chamado_id: int, com_comentarios: bool = False) -> Chamado | None:
    if not com_comentarios:
        return db.get(Chamado, chamado_id)
    return db.scalar(select(Chamado).where(Chamado.id == chamado_id)
                     .options(selectinload(Chamado.comentarios), selectinload(Chamado.avaliacao)))


def listar(db: Session, *, solicitante_id: int | None = None, status: str | None = None,
           tecnico_id: int | None = None, prioridade: str | None = None, ativo_id: int | None = None,
           busca: str | None = None, sla: str | None = None, momento: datetime | None = None,
           limite: int = 200, deslocamento: int = 0) -> list[Chamado]:
    # selectinload busca as avaliações numa consulta só (evita N+1 consultas)
    consulta = select(Chamado).options(selectinload(Chamado.avaliacao)).order_by(Chamado.id.desc())
    if solicitante_id:
        consulta = consulta.where(Chamado.solicitante_id == solicitante_id)
    if status:
        consulta = consulta.where(Chamado.status == status)
    if tecnico_id:
        consulta = consulta.where(Chamado.tecnico_id == tecnico_id)
    if prioridade:
        consulta = consulta.where(Chamado.prioridade == prioridade)
    if ativo_id:
        consulta = consulta.where(Chamado.ativo_id == ativo_id)
    if busca:
        termo = f"%{busca}%"
        filtros = [Chamado.titulo.ilike(termo), Chamado.descricao.ilike(termo)]
        if busca.isdigit():
            filtros.append(Chamado.id == int(busca))
        consulta = consulta.where(or_(*filtros))
    if sla == "vencido":
        consulta = consulta.where(Chamado.status.in_(ABERTOS), Chamado.prazo_sla < momento)
    elif sla == "alerta":
        consulta = consulta.where(Chamado.status.in_(ABERTOS), Chamado.sla_alerta_em <= momento,
                                  Chamado.prazo_sla >= momento)
    return list(db.scalars(consulta.limit(limite).offset(deslocamento)))

"""Acesso a dados do inventário (uso interno)."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modelos import Ativo


def salvar(db: Session, ativo: Ativo) -> Ativo:
    db.add(ativo)
    db.commit()
    db.refresh(ativo)
    return ativo


def buscar_por_id(db: Session, ativo_id: int) -> Ativo | None:
    return db.get(Ativo, ativo_id)


def buscar_por_patrimonio(db: Session, patrimonio: str) -> Ativo | None:
    return db.scalar(select(Ativo).where(Ativo.patrimonio == patrimonio))


def listar(db: Session, setor: str | None = None, tipo: str | None = None, situacao: str | None = None,
           responsavel_id: int | None = None, busca: str | None = None) -> list[Ativo]:
    consulta = select(Ativo).order_by(Ativo.id)
    if setor:
        consulta = consulta.where(Ativo.setor == setor)
    if tipo:
        consulta = consulta.where(Ativo.tipo == tipo)
    if situacao:
        consulta = consulta.where(Ativo.situacao == situacao)
    if responsavel_id:
        consulta = consulta.where(Ativo.responsavel_id == responsavel_id)
    if busca:
        termo = f"%{busca}%"
        consulta = consulta.where(or_(Ativo.patrimonio.ilike(termo), Ativo.descricao.ilike(termo),
                                      Ativo.modelo.ilike(termo), Ativo.numero_serie.ilike(termo)))
    return list(db.scalars(consulta))


def contar_por(db: Session, coluna) -> dict[str, int]:
    """Agrupa no banco (GROUP BY), sem carregar todos os registros."""
    return {valor: total for valor, total in db.execute(select(coluna, func.count()).group_by(coluna))}

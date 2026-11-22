"""Acesso a dados do serviço de usuários (uso interno)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modelos import Usuario


def salvar(db: Session, usuario: Usuario) -> Usuario:
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def buscar_por_id(db: Session, usuario_id: int) -> Usuario | None:
    return db.get(Usuario, usuario_id)


def buscar_por_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.email == email))


def listar(db: Session, perfil: str | None = None, somente_ativos: bool = False,
           ids: list[int] | None = None) -> list[Usuario]:
    consulta = select(Usuario).order_by(Usuario.nome)
    if perfil:
        consulta = consulta.where(Usuario.perfil == perfil)
    if somente_ativos:
        consulta = consulta.where(Usuario.ativo.is_(True))
    if ids:
        consulta = consulta.where(Usuario.id.in_(ids))
    return list(db.scalars(consulta))


def contar_admins_ativos(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Usuario)
                     .where(Usuario.perfil == "admin", Usuario.ativo.is_(True))) or 0


def existe_algum(db: Session) -> bool:
    return db.scalar(select(Usuario.id).limit(1)) is not None

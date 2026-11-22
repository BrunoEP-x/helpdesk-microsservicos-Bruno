from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.banco import Base
from helpdesk_comum.banco import agora


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (Index("ix_usuarios_perfil", "perfil"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    perfil: Mapped[str] = mapped_column(String(20))  # "solicitante", "tecnico" ou "admin"
    setor: Mapped[str | None] = mapped_column(String(80), nullable=True)
    senha_hash: Mapped[str] = mapped_column(String(200))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
    ultimo_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

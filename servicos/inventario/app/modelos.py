from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.banco import Base
from helpdesk_comum.banco import agora


class Ativo(Base):
    __tablename__ = "ativos"
    __table_args__ = (Index("ix_ativos_responsavel", "responsavel_id"), Index("ix_ativos_tipo_situacao", "tipo", "situacao"))

    id: Mapped[int] = mapped_column(primary_key=True)
    patrimonio: Mapped[str] = mapped_column(String(30), unique=True)
    tipo: Mapped[str] = mapped_column(String(30))
    descricao: Mapped[str] = mapped_column(String(200))
    setor: Mapped[str] = mapped_column(String(80))
    marca: Mapped[str | None] = mapped_column(String(60), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    numero_serie: Mapped[str | None] = mapped_column(String(80), nullable=True)
    situacao: Mapped[str] = mapped_column(String(20), default="em_uso")
    # Sem chave estrangeira: o usuário mora no banco do serviço de Usuários.
    # Guardamos o id e uma cópia do nome (para a tela funcionar mesmo se Usuários cair).
    responsavel_id: Mapped[int | None] = mapped_column(nullable=True)
    responsavel_nome: Mapped[str | None] = mapped_column(String(120), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora, onupdate=agora)

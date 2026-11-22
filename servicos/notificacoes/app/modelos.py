from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.banco import Base


class Notificacao(Base):
    __tablename__ = "notificacoes"
    __table_args__ = (
        # o mesmo evento nunca gera dois avisos para a mesma pessoa (a fila pode reentregar)
        UniqueConstraint("evento_id", "destinatario_id", name="uq_evento_destinatario"),
        Index("ix_notificacoes_destinatario_lida", "destinatario_id", "lida"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    evento_id: Mapped[str] = mapped_column(String(36))
    tipo: Mapped[str] = mapped_column(String(40))
    destinatario_id: Mapped[int]
    chamado_id: Mapped[int | None] = mapped_column(nullable=True)
    titulo: Mapped[str] = mapped_column(String(160))
    mensagem: Mapped[str] = mapped_column(String(400))
    lida: Mapped[bool] = mapped_column(Boolean, default=False)
    criada_em: Mapped[datetime] = mapped_column(DateTime)

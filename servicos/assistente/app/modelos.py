from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.banco import Base
from helpdesk_comum.banco import agora


class Artigo(Base):
    """Uma pergunta frequente com a resposta e as palavras que a identificam."""
    __tablename__ = "artigos"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(120))
    categoria: Mapped[str] = mapped_column(String(20))
    palavras_chave: Mapped[str] = mapped_column(String(600))   # separadas por vírgula
    resposta: Mapped[str] = mapped_column(Text)                 # um passo por linha
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    consultas: Mapped[int] = mapped_column(Integer, default=0)
    util_sim: Mapped[int] = mapped_column(Integer, default=0)
    util_nao: Mapped[int] = mapped_column(Integer, default=0)


class Pergunta(Base):
    """Registro das conversas, para melhorar a base (o que não foi respondido?)."""
    __tablename__ = "perguntas"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(index=True)
    texto: Mapped[str] = mapped_column(String(500))
    artigo_id: Mapped[int | None] = mapped_column(nullable=True)
    confianca: Mapped[int] = mapped_column(Integer, default=0)
    util: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime, default=agora)

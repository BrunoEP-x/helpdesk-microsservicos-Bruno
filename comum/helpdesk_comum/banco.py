"""Conexão com o banco de cada serviço e um executor simples de migrações.

Cada serviço chama `Banco(url)` com a SUA url: não existe banco compartilhado.

Migrações: cada serviço declara uma lista ordenada de `Migracao`. Ao iniciar,
as que ainda não rodaram são aplicadas e registradas na tabela `_migracoes`.
É um executor mínimo (sem dependência extra); num projeto maior, o Alembic
faria o mesmo papel.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Callable

from pydantic import PlainSerializer
from sqlalchemy import Connection, create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

log = logging.getLogger("helpdesk.banco")


def agora() -> datetime:
    """Hora atual em UTC, sem fuso (é assim que o SQLite guarda)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _como_utc(valor: datetime) -> str:
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.isoformat()


# Datas saem da API sempre com fuso (UTC). A tela converte para o horário local.
DataHora = Annotated[datetime, PlainSerializer(_como_utc, return_type=str)]


class Banco:
    def __init__(self, url: str):
        self.url = url
        argumentos = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, connect_args=argumentos, pool_pre_ping=True)
        self.Sessao = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)

    def get_db(self):
        """Abre uma sessão por requisição e fecha no final."""
        db = self.Sessao()
        try:
            yield db
        finally:
            db.close()


@dataclass(frozen=True)
class Migracao:
    versao: int
    descricao: str
    aplicar: Callable[[Connection], None]


def migrar(engine, migracoes: list[Migracao]) -> list[int]:
    """Aplica as migrações pendentes, em ordem, e devolve as versões aplicadas."""
    aplicadas: list[int] = []
    with engine.begin() as conexao:
        conexao.execute(text(
            "CREATE TABLE IF NOT EXISTS _migracoes (versao INTEGER PRIMARY KEY, descricao VARCHAR(200), "
            "aplicada_em VARCHAR(40))"
        ))
        feitas = {linha[0] for linha in conexao.execute(text("SELECT versao FROM _migracoes"))}
    for migracao in sorted(migracoes, key=lambda m: m.versao):
        if migracao.versao in feitas:
            continue
        with engine.begin() as conexao:
            migracao.aplicar(conexao)
            conexao.execute(
                text("INSERT INTO _migracoes (versao, descricao, aplicada_em) VALUES (:v, :d, :a)"),
                {"v": migracao.versao, "d": migracao.descricao, "a": agora().isoformat()},
            )
        log.info("migração %s aplicada: %s", migracao.versao, migracao.descricao)
        aplicadas.append(migracao.versao)
    return aplicadas


def adicionar_coluna_se_faltar(conexao: Connection, tabela: str, coluna: str, definicao: str) -> None:
    """Ajuda para migrações futuras: ALTER TABLE só se a coluna ainda não existir."""
    colunas = {c["name"] for c in inspect(conexao).get_columns(tabela)}
    if coluna not in colunas:
        conexao.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}"))

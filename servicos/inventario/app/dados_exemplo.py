"""Equipamentos de exemplo (DADOS_EXEMPLO=1, banco vazio). Só para aula.

Os responsáveis apontam para os ids dos usuários de exemplo do serviço de
Usuários (2 = Ana, 3 = Bruno, 4 = Carla).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos import Ativo

EXEMPLOS = [
    dict(patrimonio="PAT-0001", tipo="computador", descricao="Desktop Dell OptiPlex", setor="Financeiro",
         marca="Dell", modelo="OptiPlex 7010", responsavel_id=2, responsavel_nome="Ana Souza"),
    dict(patrimonio="PAT-0002", tipo="impressora", descricao="Impressora HP LaserJet", setor="RH",
         marca="HP", modelo="LaserJet M404", responsavel_id=3, responsavel_nome="Bruno Lima"),
    dict(patrimonio="PAT-0003", tipo="notebook", descricao="Notebook Lenovo ThinkPad", setor="TI",
         marca="Lenovo", modelo="ThinkPad E14", responsavel_id=4, responsavel_nome="Carla Dias"),
    dict(patrimonio="PAT-0004", tipo="monitor", descricao="Monitor LG 24 polegadas", setor="Financeiro",
         marca="LG", modelo="24MK430H", responsavel_id=2, responsavel_nome="Ana Souza"),
    dict(patrimonio="PAT-0005", tipo="periferico", descricao="Teclado e mouse sem fio", setor="TI",
         marca="Logitech", modelo="MK270", situacao="estoque"),
]


def carregar(db: Session) -> None:
    if db.scalar(select(Ativo.id).limit(1)) is not None:
        return
    db.add_all(Ativo(**dados) for dados in EXEMPLOS)
    db.commit()

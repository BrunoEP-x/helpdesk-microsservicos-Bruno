"""Chamados de exemplo (DADOS_EXEMPLO=1, banco vazio). Só para aula.

Usam os ids dos dados de exemplo dos outros serviços (usuários 2 = Ana,
3 = Bruno, 4 = Carla; equipamentos 1 e 2). Os eventos gerados aqui também
viram notificações, como qualquer outro chamado.
"""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import servico
from app.esquemas import ChamadoCriar
from app.modelos import Chamado
from helpdesk_comum.banco import agora
from helpdesk_comum.tokens import UsuarioToken

ANA = UsuarioToken(2, "solicitante", "Ana Souza")
BRUNO = UsuarioToken(3, "solicitante", "Bruno Lima")
CARLA = UsuarioToken(4, "tecnico", "Carla Dias")
PC = {"id": 1, "patrimonio": "PAT-0001", "descricao": "Desktop Dell OptiPlex", "tipo": "computador"}
IMPRESSORA = {"id": 2, "patrimonio": "PAT-0002", "descricao": "Impressora HP LaserJet", "tipo": "impressora"}


class _UsuariosLocal:
    """Os dados de exemplo não dependem do serviço de Usuários estar no ar."""
    def get(self, caminho, token):
        return {"id": 4, "nome": "Carla Dias", "perfil": "tecnico", "ativo": True}


def carregar(db: Session) -> None:
    if db.scalar(select(Chamado.id).limit(1)) is not None:
        return
    inicio = agora() - timedelta(hours=3)
    c1 = servico.criar(db, ChamadoCriar(titulo="Computador não liga", descricao="Apertei o botão e nada acontece.",
                                        categoria="hardware", ativo_id=1), ANA, PC, momento=inicio)
    servico.criar(db, ChamadoCriar(titulo="Impressora atolando papel", descricao="Atola a cada 3 folhas.",
                                   categoria="impressora", impacto="setor", ativo_id=2), BRUNO, IMPRESSORA, momento=inicio)
    servico.criar(db, ChamadoCriar(titulo="Acesso ao sistema de RH", descricao="Solicito acesso para a nova estagiária.",
                                   categoria="acesso"), BRUNO)
    servico.atribuir(db, c1.id, CARLA.id, CARLA, "", _UsuariosLocal())

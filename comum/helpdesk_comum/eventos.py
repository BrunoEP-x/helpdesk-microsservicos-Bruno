"""Contrato dos eventos trocados pela fila (Redis Streams).

O serviço de Chamados publica; o de Notificações consome. O contrato fica aqui
para que os dois lados usem os mesmos nomes.
"""
import json
from dataclasses import asdict, dataclass, field

STREAM = "helpdesk.eventos"
GRUPO_NOTIFICACOES = "notificacoes"

CHAMADO_ABERTO = "ChamadoAberto"
CHAMADO_ATRIBUIDO = "ChamadoAtribuido"
STATUS_ALTERADO = "StatusAlterado"
PRIORIDADE_ALTERADA = "PrioridadeAlterada"
CHAMADO_RESOLVIDO = "ChamadoResolvido"
CHAMADO_FECHADO = "ChamadoFechado"
SLA_PROXIMO = "SlaProximo"
SLA_VENCIDO = "SlaVencido"

TIPOS = (CHAMADO_ABERTO, CHAMADO_ATRIBUIDO, STATUS_ALTERADO, PRIORIDADE_ALTERADA, CHAMADO_RESOLVIDO,
         CHAMADO_FECHADO, SLA_PROXIMO, SLA_VENCIDO)


@dataclass
class Evento:
    id: str                        # identificador único (evita aviso duplicado se o evento chegar duas vezes)
    tipo: str
    chamado_id: int
    titulo: str
    destinatarios: list[int]       # ids de usuários que devem ser avisados
    avisar_equipe: bool = False    # também avisa todos os técnicos e administradores
    dados: dict = field(default_factory=dict)
    criado_em: str = ""

    def para_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def de_json(cls, texto: str) -> "Evento":
        bruto = json.loads(texto)
        return cls(**{k: bruto[k] for k in cls.__dataclass_fields__ if k in bruto})

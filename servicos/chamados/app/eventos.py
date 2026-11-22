"""Publicação de eventos com o padrão Outbox.

1. `registrar` grava o evento na tabela `eventos_pendentes`, na mesma transação
   da mudança do chamado (ou os dois são salvos, ou nenhum).
2. `publicar_pendentes` (chamado em segundo plano) envia os pendentes para o
   Redis Stream e marca como publicados. Se o Redis estiver fora do ar, os
   eventos esperam na tabela e saem na próxima tentativa.
"""
import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos import Chamado, EventoPendente
from helpdesk_comum import eventos
from helpdesk_comum.banco import agora

log = logging.getLogger("helpdesk.eventos")


def registrar(db: Session, tipo: str, chamado: Chamado, destinatarios: list[int | None],
              avisar_equipe: bool = False, **dados) -> EventoPendente:
    evento = eventos.Evento(
        id=str(uuid.uuid4()), tipo=tipo, chamado_id=chamado.id, titulo=chamado.titulo,
        destinatarios=sorted({d for d in destinatarios if d}), avisar_equipe=avisar_equipe,
        dados={"prioridade": chamado.prioridade, "status": chamado.status, **dados},
        criado_em=agora().isoformat() + "Z",
    )
    pendente = EventoPendente(id=evento.id, tipo=tipo, conteudo=evento.para_json())
    db.add(pendente)
    return pendente


def publicar_pendentes(db: Session, redis_cliente, limite: int = 100) -> int:
    pendentes = list(db.scalars(
        select(EventoPendente).where(EventoPendente.publicado_em.is_(None)).order_by(EventoPendente.criado_em).limit(limite)
    ))
    publicados = 0
    for pendente in pendentes:
        try:
            redis_cliente.xadd(eventos.STREAM, {"evento": pendente.conteudo}, maxlen=100_000, approximate=True)
        except Exception as erro:  # fila fora do ar: tenta de novo depois
            pendente.tentativas += 1
            db.commit()
            log.warning("fila indisponível; %s evento(s) aguardando (%s)", len(pendentes) - publicados, erro)
            return publicados
        pendente.publicado_em = agora()
        db.commit()
        publicados += 1
    return publicados


def como_dict(pendente: EventoPendente) -> dict:
    return json.loads(pendente.conteudo)


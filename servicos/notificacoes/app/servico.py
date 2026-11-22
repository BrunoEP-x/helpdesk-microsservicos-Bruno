"""Regras do serviço de Notificações."""
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import mensagens
from app.modelos import Notificacao
from helpdesk_comum.banco import agora
from helpdesk_comum.erros import NaoEncontrado
from helpdesk_comum.eventos import Evento


def processar(db: Session, evento: Evento, diretorio, canal_email=None) -> list[Notificacao]:
    """Transforma um evento em avisos. Idempotente: reprocessar o mesmo evento não duplica nada."""
    destinatarios = list(dict.fromkeys(evento.destinatarios))
    if evento.avisar_equipe:
        destinatarios += [i for i in diretorio.equipe() if i not in destinatarios]
    ja_avisados = set(db.scalars(select(Notificacao.destinatario_id).where(Notificacao.evento_id == evento.id)))
    novos = []
    for pessoa in destinatarios:
        if pessoa in ja_avisados:
            continue
        titulo, texto = mensagens.montar(evento, pessoa)
        novos.append(Notificacao(evento_id=evento.id, tipo=evento.tipo, destinatario_id=pessoa,
                                 chamado_id=evento.chamado_id, titulo=titulo[:160], mensagem=texto[:400],
                                 criada_em=agora()))
    db.add_all(novos)
    try:
        db.commit()
    except IntegrityError:  # outro consumidor gravou ao mesmo tempo
        db.rollback()
        return []
    if canal_email is not None:
        for n in novos:
            canal_email.enviar(n.destinatario_id, n.titulo, n.mensagem)
    return novos


def listar(db: Session, destinatario_id: int, nao_lidas: bool = False, limite: int = 50) -> list[Notificacao]:
    consulta = select(Notificacao).where(Notificacao.destinatario_id == destinatario_id)
    if nao_lidas:
        consulta = consulta.where(Notificacao.lida.is_(False))
    return list(db.scalars(consulta.order_by(Notificacao.id.desc()).limit(limite)))


def contar_nao_lidas(db: Session, destinatario_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Notificacao).where(
        Notificacao.destinatario_id == destinatario_id, Notificacao.lida.is_(False))) or 0


def marcar_lida(db: Session, notificacao_id: int, destinatario_id: int) -> Notificacao:
    aviso = db.get(Notificacao, notificacao_id)
    if aviso is None or aviso.destinatario_id != destinatario_id:
        raise NaoEncontrado("Notificação não encontrada.")
    aviso.lida = True
    db.commit()
    return aviso


def marcar_todas(db: Session, destinatario_id: int) -> int:
    resultado = db.execute(update(Notificacao).where(Notificacao.destinatario_id == destinatario_id,
                                                     Notificacao.lida.is_(False)).values(lida=True))
    db.commit()
    return resultado.rowcount

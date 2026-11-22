"""Texto de cada aviso, montado a partir do evento.

Os textos ficam no serviço de Notificações: o serviço de Chamados só diz o que
aconteceu, não como avisar.
"""
from helpdesk_comum import eventos as t
from helpdesk_comum.eventos import Evento

PRIORIDADE = {"baixa": "baixa", "media": "média", "alta": "alta", "critica": "crítica"}


def _hora(iso: str | None) -> str:
    return iso[11:16] + " UTC" if iso and len(iso) >= 16 else ""


def montar(evento: Evento, destinatario_id: int) -> tuple[str, str]:
    """Devolve (título, mensagem) para uma pessoa."""
    n, d = f"#{evento.chamado_id}", evento.dados
    eh_solicitante = destinatario_id in evento.destinatarios
    match evento.tipo:
        case t.CHAMADO_ABERTO if eh_solicitante:
            return f"Chamado {n} aberto", f"Recebemos \"{evento.titulo}\". Prioridade {PRIORIDADE.get(d.get('prioridade'), '')}."
        case t.CHAMADO_ABERTO:
            return f"Novo chamado {n}", f"{d.get('solicitante', 'Alguém')} abriu \"{evento.titulo}\" (prioridade {PRIORIDADE.get(d.get('prioridade'), '')})."
        case t.CHAMADO_ATRIBUIDO if destinatario_id == d.get("tecnico_id"):
            return f"Chamado {n} atribuído a você", f"\"{evento.titulo}\" agora é seu."
        case t.CHAMADO_ATRIBUIDO:
            return f"Chamado {n} em atendimento", f"{d.get('tecnico', 'Um técnico')} está cuidando de \"{evento.titulo}\"."
        case t.STATUS_ALTERADO:
            return f"Chamado {n}: {d.get('para', 'status alterado')}", f"{d.get('por', '')} mudou de {d.get('de')} para {d.get('para')}."
        case t.PRIORIDADE_ALTERADA:
            return (f"Prioridade do chamado {n} alterada",
                    f"De {PRIORIDADE.get(d.get('de'), d.get('de'))} para {PRIORIDADE.get(d.get('para'), d.get('para'))}."
                    + (f" Motivo: {d['motivo']}" if d.get("motivo") else ""))
        case t.CHAMADO_RESOLVIDO:
            return f"Chamado {n} resolvido", f"\"{evento.titulo}\" foi resolvido. Confirme se está tudo certo para encerrar."
        case t.CHAMADO_FECHADO:
            return f"Chamado {n} encerrado", f"\"{evento.titulo}\" foi encerrado. Que tal avaliar o atendimento?"
        case t.SLA_PROXIMO:
            return f"SLA perto de vencer: {n}", f"Faltam {d.get('minutos_restantes', '?')} min para o prazo de \"{evento.titulo}\"."
        case t.SLA_VENCIDO:
            return f"SLA vencido: {n}", f"O prazo de \"{evento.titulo}\" foi ultrapassado."
    return f"Chamado {n}", f"Atualização em \"{evento.titulo}\"."

"""Regras de negócio do serviço de Chamados.

Onde no monólito havia chamadas de função para outros módulos, agora há:
- chamadas HTTP (com timeout e token repassado) para Usuários e Inventário;
- eventos gravados na tabela de saída (outbox) para o serviço de Notificações.

Permissões:
- solicitante: abre chamados; só vê, comenta, fecha, reabre e avalia os próprios;
- técnico e admin: veem todos, atribuem, mudam status e ajustam a prioridade.

Cada operação grava o chamado, o histórico e o evento numa única transação.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app import eventos, historico, repositorio, sla
from app.esquemas import AvaliacaoCriar, ChamadoCriar, ComentarioCriar
from app.modelos import ABERTOS, Avaliacao, Chamado, Comentario
from app.prioridade import sugerir
from helpdesk_comum import eventos as tipos
from helpdesk_comum.banco import agora
from helpdesk_comum.clientes import ClienteServico
from helpdesk_comum.erros import NaoEncontrado, RegraDeNegocio, SemPermissao
from helpdesk_comum.tokens import UsuarioToken

# De qual status para quais status um chamado pode ir (mesmas regras do monólito)
TRANSICOES = {
    "aberto": {"em_atendimento"},
    "em_atendimento": {"resolvido"},
    "resolvido": {"fechado", "em_atendimento"},  # reabrir se o problema voltar
    "fechado": set(),
}
ROTULO_STATUS = {"aberto": "Aberto", "em_atendimento": "Em andamento", "resolvido": "Resolvido", "fechado": "Encerrado"}


# ---------------------------------------------------------------- abertura

def abrir(db: Session, dados: ChamadoCriar, usuario: UsuarioToken, token: str,
          inventario: ClienteServico) -> Chamado:
    ativo = None
    if dados.ativo_id is not None:
        ativo = inventario.get(f"/ativos/{dados.ativo_id}", token)          # chamada HTTP ao Inventário
    return criar(db, dados, usuario, ativo)


def criar(db: Session, dados: ChamadoCriar, usuario: UsuarioToken, ativo: dict | None = None,
          momento: datetime | None = None) -> Chamado:
    momento = momento or agora()
    sugestao = sugerir(dados.titulo, dados.descricao, dados.impacto, dados.categoria,
                       ativo.get("tipo") if ativo else None)
    prioridade = dados.prioridade or sugestao.prioridade
    prazo, alerta = sla.calcular_prazos(db, prioridade, momento)
    chamado = Chamado(
        titulo=dados.titulo, descricao=dados.descricao, categoria=dados.categoria, impacto=dados.impacto,
        prioridade=prioridade, prioridade_sugerida=sugestao.prioridade,
        prioridade_origem="informada" if dados.prioridade else "automatica",
        status="aberto", solicitante_id=usuario.id, solicitante_nome=usuario.nome,
        ativo_id=ativo["id"] if ativo else None,
        ativo_descricao=f"{ativo['patrimonio']} · {ativo['descricao']}" if ativo else None,
        criado_em=momento, prazo_sla=prazo, sla_alerta_em=alerta,
    )
    db.add(chamado)
    db.flush()  # gera o id
    historico.registrar(db, chamado.id, "abertura", usuario, detalhe=(
        f"Prioridade {prioridade} ({chamado.prioridade_origem}); sugerida: {sugestao.prioridade} — "
        + "; ".join(sugestao.motivos)))
    eventos.registrar(db, tipos.CHAMADO_ABERTO, chamado, [usuario.id], avisar_equipe=True,
                      prazo=prazo.isoformat() + "Z", solicitante=usuario.nome)
    db.commit()
    return chamado


# ---------------------------------------------------------------- consulta

def obter(db: Session, chamado_id: int, usuario: UsuarioToken, com_comentarios: bool = False) -> Chamado:
    chamado = repositorio.buscar_por_id(db, chamado_id, com_comentarios)
    # Para quem não pode ver, responde "não encontrado": não revela que o chamado existe
    if chamado is None or not (usuario.eh_equipe or chamado.solicitante_id == usuario.id):
        raise NaoEncontrado(f"Chamado {chamado_id} não encontrado.")
    return chamado


def detalhar(db: Session, chamado_id: int, usuario: UsuarioToken) -> dict:
    chamado = obter(db, chamado_id, usuario, com_comentarios=True)
    from app.esquemas import ChamadoDetalhe
    saida = ChamadoDetalhe.model_validate(chamado)
    if not usuario.eh_equipe:  # notas internas da equipe não aparecem para o solicitante
        saida.comentarios = [c for c in saida.comentarios if not c.interno]
    return saida


def listar(db: Session, usuario: UsuarioToken, **filtros) -> list[Chamado]:
    if not usuario.eh_equipe:
        filtros["solicitante_id"] = usuario.id
    return repositorio.listar(db, momento=agora(), **filtros)


def consultar_historico(db: Session, chamado_id: int, usuario: UsuarioToken):
    obter(db, chamado_id, usuario)  # confere a permissão
    return historico.listar(db, chamado_id)


# ---------------------------------------------------------------- atendimento

def _exigir_equipe(usuario: UsuarioToken, acao: str) -> None:
    if not usuario.eh_equipe:
        raise SemPermissao(f"Só técnicos e administradores {acao}.")


def atribuir(db: Session, chamado_id: int, tecnico_id: int, usuario: UsuarioToken, token: str,
             usuarios: ClienteServico) -> Chamado:
    _exigir_equipe(usuario, "atribuem chamados")
    chamado = obter(db, chamado_id, usuario)
    if chamado.status not in ABERTOS:
        raise RegraDeNegocio("Não é possível atribuir um chamado resolvido ou fechado.")
    tecnico = usuarios.get(f"/usuarios/{tecnico_id}", token)                # chamada HTTP a Usuários
    if tecnico.get("perfil") != "tecnico":
        raise RegraDeNegocio(f"Usuário {tecnico_id} não é técnico.")
    if not tecnico.get("ativo", True):
        raise RegraDeNegocio(f"O técnico {tecnico['nome']} está desativado.")

    anterior = chamado.tecnico_nome
    chamado.tecnico_id, chamado.tecnico_nome = tecnico["id"], tecnico["nome"]
    chamado.atribuido_em = chamado.atribuido_em or agora()
    historico.registrar(db, chamado.id, "atribuicao", usuario, "tecnico", anterior, tecnico["nome"])
    if chamado.status == "aberto":
        chamado.status = "em_atendimento"
        historico.registrar(db, chamado.id, "status", usuario, "status", "aberto", "em_atendimento")
    eventos.registrar(db, tipos.CHAMADO_ATRIBUIDO, chamado, [tecnico["id"], chamado.solicitante_id],
                      tecnico=tecnico["nome"], tecnico_id=tecnico["id"])
    db.commit()
    return chamado


def mudar_status(db: Session, chamado_id: int, novo: str, usuario: UsuarioToken, solucao: str | None = None) -> Chamado:
    chamado = obter(db, chamado_id, usuario)
    # O solicitante só pode confirmar (fechar) ou reabrir o próprio chamado resolvido
    pode_solicitante = chamado.status == "resolvido" and novo in ("fechado", "em_atendimento")
    if not (usuario.eh_equipe or pode_solicitante):
        raise SemPermissao("Você não pode mudar o status deste chamado.")
    if novo not in TRANSICOES[chamado.status]:
        raise RegraDeNegocio(f"Não é possível ir de '{chamado.status}' para '{novo}'.")
    if novo == "em_atendimento" and chamado.tecnico_id is None:
        raise RegraDeNegocio("Atribua um técnico antes de iniciar o atendimento.")

    anterior, momento = chamado.status, agora()
    chamado.status = novo
    historico.registrar(db, chamado.id, "status", usuario, "status", anterior, novo)

    if novo == "resolvido":
        chamado.resolvido_em = momento
        if solucao:
            chamado.solucao = solucao
            historico.registrar(db, chamado.id, "solucao", usuario, "solucao", None, solucao)
        if momento > chamado.prazo_sla and not chamado.sla_violado:
            sla.marcar_violacao(db, chamado)
        eventos.registrar(db, tipos.CHAMADO_RESOLVIDO, chamado, [chamado.solicitante_id], solucao=solucao or "")
    elif novo == "fechado":
        chamado.fechado_em = momento
        historico.registrar(db, chamado.id, "encerramento", usuario, detalhe="Atendimento encerrado.")
        eventos.registrar(db, tipos.CHAMADO_FECHADO, chamado, [chamado.solicitante_id, chamado.tecnico_id])
    else:  # reaberto: volta para atendimento
        chamado.resolvido_em = None
        eventos.registrar(db, tipos.STATUS_ALTERADO, chamado, [chamado.solicitante_id, chamado.tecnico_id],
                          de=ROTULO_STATUS[anterior], para=ROTULO_STATUS[novo], por=usuario.nome)
    db.commit()
    return chamado


def mudar_prioridade(db: Session, chamado_id: int, prioridade: str, motivo: str | None,
                     usuario: UsuarioToken) -> Chamado:
    """Ajuste manual. O prazo do SLA é recalculado a partir da abertura do chamado."""
    _exigir_equipe(usuario, "ajustam a prioridade")
    chamado = obter(db, chamado_id, usuario)
    if chamado.status not in ABERTOS:
        raise RegraDeNegocio("Só é possível ajustar a prioridade de chamados em aberto.")
    if prioridade == chamado.prioridade:
        return chamado
    anterior = chamado.prioridade
    chamado.prioridade, chamado.prioridade_origem = prioridade, "ajuste_manual"
    chamado.prazo_sla, chamado.sla_alerta_em = sla.calcular_prazos(db, prioridade, chamado.criado_em)
    momento = agora()
    if chamado.prazo_sla > momento:  # o novo prazo ainda não venceu: os alertas voltam a valer
        chamado.sla_violado, chamado.sla_violado_em = False, None
        chamado.sla_alerta_enviado = chamado.sla_alerta_em <= momento and chamado.sla_alerta_enviado
    historico.registrar(db, chamado.id, "prioridade", usuario, "prioridade", anterior, prioridade, motivo)
    eventos.registrar(db, tipos.PRIORIDADE_ALTERADA, chamado, [chamado.solicitante_id, chamado.tecnico_id],
                      de=anterior, para=prioridade, prazo=chamado.prazo_sla.isoformat() + "Z", motivo=motivo or "")
    db.commit()
    return chamado


def comentar(db: Session, chamado_id: int, dados: ComentarioCriar, usuario: UsuarioToken) -> Comentario:
    chamado = obter(db, chamado_id, usuario)
    if chamado.status == "fechado":
        raise RegraDeNegocio("Chamados fechados não recebem comentários.")
    if dados.interno and not usuario.eh_equipe:
        raise SemPermissao("Só a equipe técnica escreve notas internas.")
    comentario = Comentario(chamado_id=chamado.id, autor_id=usuario.id, autor_nome=usuario.nome,
                            texto=dados.texto, interno=dados.interno, criado_em=agora())
    db.add(comentario)
    historico.registrar(db, chamado.id, "comentario", usuario, detalhe="Nota interna" if dados.interno else "Comentário")
    db.commit()
    db.refresh(comentario)
    return comentario


# ---------------------------------------------------------------- avaliação

def avaliar(db: Session, chamado_id: int, dados: AvaliacaoCriar, usuario: UsuarioToken) -> Avaliacao:
    chamado = obter(db, chamado_id, usuario)
    if chamado.solicitante_id != usuario.id:
        raise SemPermissao("Só quem abriu o chamado pode avaliar o atendimento.")
    if chamado.status != "fechado":
        raise RegraDeNegocio("A avaliação fica disponível quando o chamado é encerrado.")
    if chamado.avaliacao is not None:
        raise RegraDeNegocio("Este atendimento já foi avaliado.")
    avaliacao = Avaliacao(chamado_id=chamado.id, nota=dados.nota, comentario=dados.comentario,
                          tecnico_id=chamado.tecnico_id, tecnico_nome=chamado.tecnico_nome, autor_id=usuario.id)
    db.add(avaliacao)
    historico.registrar(db, chamado.id, "avaliacao", usuario, "nota", None, dados.nota)
    db.commit()
    db.refresh(avaliacao)
    return avaliacao

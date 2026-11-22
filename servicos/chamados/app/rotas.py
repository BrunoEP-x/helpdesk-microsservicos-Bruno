from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app import painel as indicadores
from app import servico, sla
from app.banco import get_db
from app.clientes import cliente_inventario, cliente_usuarios
from app.esquemas import (
    Atribuicao, AvaliacaoCriar, AvaliacaoSaida, ChamadoCriar, ChamadoDetalhe, ChamadoSaida, ComentarioCriar,
    ComentarioSaida, HistoricoSaida, ItemSla, MudancaPrioridade, MudancaStatus, Painel, PedidoSugestao, Prioridade,
    RelatorioSatisfacao, Status, SugestaoSaida,
)
from app.prioridade import sugerir
from helpdesk_comum.auth import exigir_perfil, token_bruto, usuario_pessoa
from helpdesk_comum.clientes import ClienteServico
from helpdesk_comum.tokens import UsuarioToken

router = APIRouter(prefix="/chamados", tags=["Chamados"])
Usuario = UsuarioToken


@router.post("", response_model=ChamadoSaida, status_code=201)
def abrir_chamado(dados: ChamadoCriar, usuario: Usuario = Depends(usuario_pessoa), token: str = Depends(token_bruto),
                  db: Session = Depends(get_db), inventario: ClienteServico = Depends(cliente_inventario)):
    return servico.abrir(db, dados, usuario, token, inventario)


@router.get("", response_model=list[ChamadoSaida])
def listar_chamados(status: Status | None = None, tecnico_id: int | None = Query(None, gt=0),
                    prioridade: Prioridade | None = None, ativo_id: int | None = Query(None, gt=0),
                    busca: str | None = Query(None, max_length=80), sla: Literal["vencido", "alerta"] | None = None,
                    limite: int = Query(200, ge=1, le=500), deslocamento: int = Query(0, ge=0),
                    usuario: Usuario = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    return servico.listar(db, usuario, status=status, tecnico_id=tecnico_id, prioridade=prioridade, ativo_id=ativo_id,
                          busca=busca, sla=sla, limite=limite, deslocamento=deslocamento)


@router.post("/sugerir-prioridade", response_model=SugestaoSaida)
def sugerir_prioridade(dados: PedidoSugestao, usuario: Usuario = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    """Mostra, enquanto a pessoa digita, qual prioridade o sistema vai sugerir e por quê."""
    s = sugerir(dados.titulo, dados.descricao, dados.impacto, dados.categoria)
    return {"prioridade": s.prioridade, "pontos": s.pontos, "motivos": s.motivos,
            "prazo_horas": sla.configuracao(db)[s.prioridade][0]}


@router.get("/painel", response_model=Painel)
def painel(apenas_meus: bool = False, usuario: Usuario = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    return indicadores.painel(db, usuario, apenas_meus)


@router.get("/sla", response_model=list[ItemSla])
def ver_sla(usuario: Usuario = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    return [{"prioridade": p, "horas": h, "alerta_percentual": a} for p, (h, a) in sla.configuracao(db).items()]


@router.put("/sla", response_model=list[ItemSla], dependencies=[Depends(exigir_perfil("admin"))])
def configurar_sla(itens: list[ItemSla], db: Session = Depends(get_db)):
    novos = sla.atualizar_configuracao(db, [i.model_dump() for i in itens])
    return [{"prioridade": p, "horas": h, "alerta_percentual": a} for p, (h, a) in novos.items()]


@router.post("/sla/verificar", dependencies=[Depends(exigir_perfil("admin"))])
def verificar_sla_agora(db: Session = Depends(get_db)):
    """Roda a verificação de prazos na hora (ela também roda sozinha a cada minuto)."""
    return sla.verificar(db)


@router.get("/relatorios/satisfacao", response_model=RelatorioSatisfacao,
            dependencies=[Depends(exigir_perfil("tecnico", "admin"))])
def relatorio_satisfacao(usuario: Usuario = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    return indicadores.satisfacao(db, usuario)


@router.get("/relatorios/chamados.csv", dependencies=[Depends(exigir_perfil("admin"))])
def exportar_csv(db: Session = Depends(get_db)):
    return Response(indicadores.exportar_csv(db), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="chamados.csv"'})


@router.get("/{chamado_id}", response_model=ChamadoDetalhe)
def obter_chamado(chamado_id: int, usuario: Usuario = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    return servico.detalhar(db, chamado_id, usuario)


@router.get("/{chamado_id}/historico", response_model=list[HistoricoSaida])
def historico(chamado_id: int, usuario: Usuario = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    return servico.consultar_historico(db, chamado_id, usuario)


@router.patch("/{chamado_id}/atribuir", response_model=ChamadoSaida)
def atribuir_chamado(chamado_id: int, dados: Atribuicao, usuario: Usuario = Depends(usuario_pessoa),
                     token: str = Depends(token_bruto), db: Session = Depends(get_db),
                     usuarios: ClienteServico = Depends(cliente_usuarios)):
    return servico.atribuir(db, chamado_id, dados.tecnico_id, usuario, token, usuarios)


@router.patch("/{chamado_id}/status", response_model=ChamadoSaida)
def mudar_status(chamado_id: int, dados: MudancaStatus, usuario: Usuario = Depends(usuario_pessoa),
                 db: Session = Depends(get_db)):
    return servico.mudar_status(db, chamado_id, dados.status, usuario, dados.solucao)


@router.patch("/{chamado_id}/prioridade", response_model=ChamadoSaida)
def mudar_prioridade(chamado_id: int, dados: MudancaPrioridade, usuario: Usuario = Depends(usuario_pessoa),
                     db: Session = Depends(get_db)):
    return servico.mudar_prioridade(db, chamado_id, dados.prioridade, dados.motivo, usuario)


@router.post("/{chamado_id}/comentarios", response_model=ComentarioSaida, status_code=201)
def comentar(chamado_id: int, dados: ComentarioCriar, usuario: Usuario = Depends(usuario_pessoa),
             db: Session = Depends(get_db)):
    return servico.comentar(db, chamado_id, dados, usuario)


@router.post("/{chamado_id}/avaliacao", response_model=AvaliacaoSaida, status_code=201)
def avaliar(chamado_id: int, dados: AvaliacaoCriar, usuario: Usuario = Depends(usuario_pessoa),
            db: Session = Depends(get_db)):
    return servico.avaliar(db, chamado_id, dados, usuario)

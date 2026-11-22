from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import servico
from app.banco import get_db
from app.clientes import cliente_usuarios
from app.esquemas import AtivoAtualizar, AtivoCriar, AtivoSaida, Resumo, Situacao, TipoAtivo
from helpdesk_comum.auth import exigir_perfil, token_bruto, usuario_atual
from helpdesk_comum.clientes import ClienteServico

router = APIRouter(prefix="/ativos", tags=["Inventário"])
equipe = exigir_perfil("tecnico", "admin")


@router.post("", response_model=AtivoSaida, status_code=201, dependencies=[Depends(equipe)])
def criar_ativo(dados: AtivoCriar, db: Session = Depends(get_db), token: str = Depends(token_bruto),
                usuarios: ClienteServico = Depends(cliente_usuarios)):
    return servico.criar(db, dados, usuarios, token)


@router.get("", response_model=list[AtivoSaida], dependencies=[Depends(usuario_atual)])
def listar_ativos(setor: str | None = Query(None, max_length=80), tipo: TipoAtivo | None = None,
                  situacao: Situacao | None = None, responsavel_id: int | None = Query(None, gt=0),
                  busca: str | None = Query(None, max_length=80), db: Session = Depends(get_db)):
    return servico.listar(db, setor=setor, tipo=tipo, situacao=situacao, responsavel_id=responsavel_id, busca=busca)


@router.get("/resumo", response_model=Resumo, dependencies=[Depends(equipe)])
def resumo(db: Session = Depends(get_db)):
    return servico.resumo(db)


@router.get("/{ativo_id}", response_model=AtivoSaida, dependencies=[Depends(usuario_atual)])
def obter_ativo(ativo_id: int, db: Session = Depends(get_db)):
    return servico.obter(db, ativo_id)


@router.patch("/{ativo_id}", response_model=AtivoSaida, dependencies=[Depends(equipe)])
def atualizar_ativo(ativo_id: int, dados: AtivoAtualizar, db: Session = Depends(get_db),
                    token: str = Depends(token_bruto), usuarios: ClienteServico = Depends(cliente_usuarios)):
    return servico.atualizar(db, ativo_id, dados, usuarios, token)

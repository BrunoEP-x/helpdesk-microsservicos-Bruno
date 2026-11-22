"""Regras do serviço Assistente."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import motor
from app.esquemas import ArtigoEntrada
from app.modelos import Artigo, Pergunta
from helpdesk_comum.erros import NaoEncontrado, SemPermissao
from helpdesk_comum.tokens import UsuarioToken

MENSAGENS = {
    "cumprimento": "Olá! Sou o assistente do HelpDesk Pro. Descreva o problema com suas palavras, por exemplo: "
                   "\"estou sem internet\" ou \"a impressora não imprime\".",
    "agradecimento": "Que bom que ajudou! Se precisar, é só chamar.",
    "atendente": "Tudo bem! Você pode abrir um chamado e um técnico vai atender. Já deixei o formulário preparado.",
    "sugestoes": "Não tenho certeza se entendi. Algum destes assuntos é o seu problema?",
    "sem_resposta": "Não encontrei uma solução para isso na minha base. Recomendo abrir um chamado: "
                    "um técnico vai analisar o seu caso.",
}


def artigos_ativos(db: Session) -> list[Artigo]:
    return list(db.scalars(select(Artigo).where(Artigo.ativo.is_(True)).order_by(Artigo.id)))


def perguntar(db: Session, texto: str, usuario: UsuarioToken) -> dict:
    resultado = motor.responder(texto, artigos_ativos(db))
    artigo = resultado.artigo
    pergunta = Pergunta(usuario_id=usuario.id, texto=texto[:500], artigo_id=artigo.id if artigo else None,
                        confianca=resultado.pontos)
    db.add(pergunta)
    if artigo:
        artigo.consultas += 1
    db.commit()

    abrir = resultado.tipo in ("sem_resposta", "atendente", "sugestoes", "resposta")
    sugerido = None
    if resultado.tipo in ("sem_resposta", "atendente", "sugestoes", "resposta"):
        sugerido = {"titulo": (artigo.titulo if artigo else texto)[:120] if len(texto) >= 3 else "Preciso de ajuda",
                    "descricao": texto if len(texto) >= 3 else "Preciso de ajuda do suporte.",
                    "categoria": artigo.categoria if artigo else "outro"}
    if resultado.tipo == "resposta":
        mensagem = f"Encontrei isto sobre \"{artigo.titulo}\". Tente estes passos:"
    else:
        mensagem = MENSAGENS[resultado.tipo]
    return {
        "pergunta_id": pergunta.id, "tipo": resultado.tipo, "mensagem": mensagem,
        "passos": [p.strip() for p in artigo.resposta.splitlines() if p.strip()] if artigo else [],
        "artigo": artigo, "sugestoes": resultado.sugestoes,
        # depois de uma resposta, o botão de chamado aparece se a pessoa disser que não resolveu
        "abrir_chamado": abrir and resultado.tipo != "resposta",
        "chamado_sugerido": sugerido,
    }


def ver_artigo(db: Session, artigo_id: int, usuario: UsuarioToken) -> dict:
    """Quando a pessoa escolhe uma das sugestões."""
    artigo = db.get(Artigo, artigo_id)
    if artigo is None or not artigo.ativo:
        raise NaoEncontrado("Artigo não encontrado.")
    return perguntar(db, artigo.titulo + " " + artigo.palavras_chave, usuario)


def registrar_feedback(db: Session, pergunta_id: int, util: bool, usuario: UsuarioToken) -> None:
    pergunta = db.get(Pergunta, pergunta_id)
    if pergunta is None or pergunta.usuario_id != usuario.id:
        raise NaoEncontrado("Pergunta não encontrada.")
    if pergunta.util is None and pergunta.artigo_id:
        artigo = db.get(Artigo, pergunta.artigo_id)
        if artigo:
            if util:
                artigo.util_sim += 1
            else:
                artigo.util_nao += 1
    pergunta.util = util
    db.commit()


def listar_artigos(db: Session, usuario: UsuarioToken) -> list[Artigo]:
    consulta = select(Artigo).order_by(Artigo.categoria, Artigo.titulo)
    if not usuario.eh_admin:
        consulta = consulta.where(Artigo.ativo.is_(True))
    return list(db.scalars(consulta))


def salvar_artigo(db: Session, dados: ArtigoEntrada, artigo_id: int | None = None) -> Artigo:
    artigo = db.get(Artigo, artigo_id) if artigo_id else Artigo(consultas=0, util_sim=0, util_nao=0)
    if artigo is None:
        raise NaoEncontrado("Artigo não encontrado.")
    for campo, valor in dados.model_dump().items():
        setattr(artigo, campo, valor)
    db.add(artigo)
    db.commit()
    db.refresh(artigo)
    return artigo


def estatisticas(db: Session) -> dict:
    total = db.scalar(select(func.count()).select_from(Pergunta)) or 0
    respondidas = db.scalar(select(func.count()).select_from(Pergunta).where(Pergunta.artigo_id.is_not(None))) or 0
    uteis = db.scalar(select(func.count()).select_from(Pergunta).where(Pergunta.util.is_(True))) or 0
    nao_uteis = db.scalar(select(func.count()).select_from(Pergunta).where(Pergunta.util.is_(False))) or 0
    sem_resposta = db.scalars(select(Pergunta.texto).where(Pergunta.artigo_id.is_(None), Pergunta.confianca < 3)
                              .order_by(Pergunta.id.desc()).limit(10)).all()
    mais = db.scalars(select(Artigo).order_by(Artigo.consultas.desc()).limit(5)).all()
    return {"perguntas": total, "respondidas": respondidas, "uteis": uteis, "nao_uteis": nao_uteis,
            "sem_resposta_recentes": list(sem_resposta), "mais_consultados": list(mais)}


def exigir_admin(usuario: UsuarioToken) -> None:
    if not usuario.eh_admin:
        raise SemPermissao("Só administradores editam a base de conhecimento.")

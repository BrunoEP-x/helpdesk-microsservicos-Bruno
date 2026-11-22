"""Consumidor da fila de eventos (Redis Streams com grupo de consumo).

- O grupo guarda a posição de leitura: se o serviço cair, ao voltar ele continua
  de onde parou e nenhum evento se perde.
- Só confirma (XACK) depois de gravar o aviso. Se algo falhar (por exemplo,
  Usuários fora do ar ao buscar a equipe), o evento fica pendente e é
  reprocessado na próxima volta.
"""
import logging
import threading
import time

from app import config, servico
from app.banco import banco
from app.diretorio import DiretorioUsuarios
from app.email import CanalEmail
from helpdesk_comum import eventos
from helpdesk_comum.eventos import Evento

log = logging.getLogger("helpdesk.consumidor")

estado = {"ativo": False, "processados": 0, "ultimo_evento": None, "ultimo_erro": None}
_parar = threading.Event()


def _garantir_grupo(redis_cliente) -> None:
    try:
        redis_cliente.xgroup_create(eventos.STREAM, eventos.GRUPO_NOTIFICACOES, id="0", mkstream=True)
    except Exception as erro:
        if "BUSYGROUP" not in str(erro):
            raise


def _tratar(redis_cliente, mensagens, diretorio, canal) -> None:
    for _stream, itens in mensagens:
        for msg_id, campos in itens:
            bruto = campos.get(b"evento") or campos.get("evento")
            evento = Evento.de_json(bruto.decode() if isinstance(bruto, bytes) else bruto)
            with banco.Sessao() as db:
                servico.processar(db, evento, diretorio, canal)
            redis_cliente.xack(eventos.STREAM, eventos.GRUPO_NOTIFICACOES, msg_id)
            estado["processados"] += 1
            estado["ultimo_evento"] = evento.tipo
            log.info("evento %s do chamado #%s processado", evento.tipo, evento.chamado_id)


def _laco() -> None:
    import redis
    redis_cliente = redis.Redis.from_url(config.REDIS_URL, socket_timeout=10, socket_connect_timeout=3)
    diretorio = DiretorioUsuarios()
    canal = CanalEmail(diretorio)
    while not _parar.is_set():
        try:
            _garantir_grupo(redis_cliente)
            estado["ativo"] = True
            # primeiro os pendentes (que falharam antes), depois os novos
            for posicao in ("0", ">"):
                mensagens = redis_cliente.xreadgroup(eventos.GRUPO_NOTIFICACOES, config.NOME_CONSUMIDOR,
                                                     {eventos.STREAM: posicao}, count=50,
                                                     block=None if posicao == "0" else 5000)
                _tratar(redis_cliente, mensagens or [], diretorio, canal)
            estado["ultimo_erro"] = None
        except Exception as erro:
            estado["ativo"], estado["ultimo_erro"] = False, str(erro)[:200]
            log.warning("consumidor aguardando a fila ou os serviços: %s", erro)
            time.sleep(3)


def iniciar() -> None:
    if not config.REDIS_URL:
        log.warning("REDIS_URL não definido: o consumidor de eventos não foi iniciado")
        return
    _parar.clear()
    threading.Thread(target=_laco, daemon=True, name="consumidor").start()


def parar() -> None:
    _parar.set()

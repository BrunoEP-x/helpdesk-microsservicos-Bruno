"""Tarefas em segundo plano do serviço de Chamados.

- publicador: envia os eventos da tabela de saída para o Redis Stream;
- verificador de SLA: a cada minuto, gera alertas de vencimento e registra violações.

Rodam em threads simples (o serviço tem uma instância). Com várias instâncias,
o ideal seria um agendador dedicado ou um lock no Redis.
"""
import logging
import threading

from app import config, eventos, sla
from app.banco import banco

log = logging.getLogger("helpdesk.tarefas")
_parar = threading.Event()


def _laco(nome: str, intervalo: float, trabalho) -> None:
    while not _parar.wait(intervalo):
        try:
            trabalho()
        except Exception:
            log.exception("falha na tarefa %s", nome)


def _publicar(redis_cliente) -> None:
    with banco.Sessao() as db:
        if (n := eventos.publicar_pendentes(db, redis_cliente)):
            log.info("%s evento(s) publicados na fila", n)


def _verificar_sla() -> None:
    with banco.Sessao() as db:
        resultado = sla.verificar(db)
        if any(resultado.values()):
            log.info("verificação de SLA: %s", resultado)


def iniciar() -> None:
    _parar.clear()
    if config.REDIS_URL:
        import redis
        cliente = redis.Redis.from_url(config.REDIS_URL, socket_timeout=2, socket_connect_timeout=2)
        threading.Thread(target=_laco, args=("publicador", config.INTERVALO_PUBLICACAO, lambda: _publicar(cliente)),
                         daemon=True).start()
    else:
        log.warning("REDIS_URL não definido: eventos ficam guardados na tabela de saída")
    threading.Thread(target=_laco, args=("sla", config.INTERVALO_VERIFICACAO_SLA, _verificar_sla), daemon=True).start()


def parar() -> None:
    _parar.set()

"""Limite de tentativas de login.

Depois de várias senhas erradas para o mesmo e-mail e endereço, o login fica
bloqueado por alguns minutos. Com REDIS_URL definido, a contagem fica no Redis
(compartilhada entre várias instâncias do serviço); sem ele, fica em memória.
Se o Redis cair, volta para a memória em vez de derrubar o login.
"""
import logging
import time
from collections import defaultdict
from threading import Lock

from app import config

log = logging.getLogger("helpdesk.limite")


class LimiteMemoria:
    def __init__(self):
        self._falhas: dict[str, list[float]] = defaultdict(list)
        self._trava = Lock()

    def _recentes(self, chave: str, agora: float) -> list[float]:
        self._falhas[chave] = [t for t in self._falhas[chave] if agora - t < config.LOGIN_JANELA_SEGUNDOS]
        return self._falhas[chave]

    def bloqueado(self, chave: str) -> bool:
        with self._trava:
            return len(self._recentes(chave, time.monotonic())) >= config.LOGIN_MAX_FALHAS

    def registrar_falha(self, chave: str) -> None:
        with self._trava:
            agora = time.monotonic()
            self._recentes(chave, agora).append(agora)

    def limpar(self, chave: str) -> None:
        with self._trava:
            self._falhas.pop(chave, None)

    def limpar_tudo(self) -> None:
        with self._trava:
            self._falhas.clear()


class LimiteRedis:
    def __init__(self, url: str):
        import redis
        self._redis = redis.Redis.from_url(url, socket_timeout=1, socket_connect_timeout=1)
        self._reserva = LimiteMemoria()

    def _chave(self, chave: str) -> str:
        return f"login:falhas:{chave}"

    def bloqueado(self, chave: str) -> bool:
        try:
            return int(self._redis.get(self._chave(chave)) or 0) >= config.LOGIN_MAX_FALHAS
        except Exception:
            log.warning("Redis indisponível; usando limite em memória")
            return self._reserva.bloqueado(chave)

    def registrar_falha(self, chave: str) -> None:
        try:
            pipe = self._redis.pipeline()
            pipe.incr(self._chave(chave))
            pipe.expire(self._chave(chave), config.LOGIN_JANELA_SEGUNDOS)
            pipe.execute()
        except Exception:
            self._reserva.registrar_falha(chave)

    def limpar(self, chave: str) -> None:
        try:
            self._redis.delete(self._chave(chave))
        except Exception:
            pass
        self._reserva.limpar(chave)

    def limpar_tudo(self) -> None:
        self._reserva.limpar_tudo()


limite = LimiteRedis(config.REDIS_URL) if config.REDIS_URL else LimiteMemoria()

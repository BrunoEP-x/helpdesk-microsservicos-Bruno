"""Testes da biblioteca comum: tokens, cliente entre serviços e migrações."""
from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest
from sqlalchemy import text

from helpdesk_comum import config, tokens
from helpdesk_comum.banco import Banco, Migracao, migrar
from helpdesk_comum.clientes import ClienteServico
from helpdesk_comum.erros import NaoEncontrado, ServicoIndisponivel


def test_token_ida_e_volta():
    token, _ = tokens.criar(7, "tecnico", "Carla")
    u = tokens.ler(token)
    assert (u.id, u.perfil, u.nome, u.eh_equipe) == (7, "tecnico", "Carla", True)


def test_token_com_perfil_desconhecido_e_recusado():
    agora = datetime.now(timezone.utc)
    falso = jwt.encode({"sub": "1", "perfil": "root", "iss": config.JWT_EMISSOR, "iat": agora,
                        "exp": agora + timedelta(minutes=5)}, config.jwt_segredo(), algorithm="HS256")
    with pytest.raises(tokens.TokenInvalido):
        tokens.ler(falso)


def test_token_de_servico():
    u = tokens.ler(tokens.criar_de_servico("notificacoes"))
    assert u.eh_servico and u.id == 0


def test_segredo_curto_e_recusado(monkeypatch):
    monkeypatch.setenv("JWT_SEGREDO", "curto")
    monkeypatch.delenv("JWT_SEGREDO_ARQUIVO", raising=False)
    with pytest.raises(config.SegredoAusente):
        config.jwt_segredo()


def test_segredo_lido_de_arquivo(monkeypatch, tmp_path):
    arquivo = tmp_path / "jwt"
    arquivo.write_text("x" * 40)
    monkeypatch.delenv("JWT_SEGREDO", raising=False)
    monkeypatch.setenv("JWT_SEGREDO_ARQUIVO", str(arquivo))
    assert config.jwt_segredo() == "x" * 40


def test_cliente_servico_fora_do_ar_vira_503():
    # porta 9 (discard) não tem ninguém ouvindo: conexão recusada na hora
    cliente = ClienteServico("Inventário", "http://127.0.0.1:9", timeout=0.5)
    with pytest.raises(ServicoIndisponivel, match="Inventário"):
        cliente.get("/ativos/1", "token")


def test_cliente_timeout_vira_503():
    def lento(request):
        raise httpx.ReadTimeout("demorou", request=request)
    cliente = ClienteServico("Usuários", "http://usuarios", transporte=httpx.MockTransport(lento))
    with pytest.raises(ServicoIndisponivel, match="não respondeu a tempo"):
        cliente.get("/usuarios/1", "token")


def test_cliente_repassa_token_e_traduz_404():
    vistos = []
    def servidor(request):
        vistos.append(request.headers["authorization"])
        return httpx.Response(404, json={"detail": "Usuário 9 não encontrado."})
    cliente = ClienteServico("Usuários", "http://usuarios", transporte=httpx.MockTransport(servidor))
    with pytest.raises(NaoEncontrado, match="Usuário 9"):
        cliente.get("/usuarios/9", "abc")
    assert vistos == ["Bearer abc"]


def test_migracoes_rodam_uma_vez_so():
    banco = Banco("sqlite://")
    m = [Migracao(1, "cria tabela", lambda c: c.execute(text("CREATE TABLE t (id INTEGER)"))),
         Migracao(2, "insere", lambda c: c.execute(text("INSERT INTO t VALUES (1)")))]
    assert migrar(banco.engine, m) == [1, 2]
    assert migrar(banco.engine, m) == []
    with banco.engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM t")).scalar() == 1

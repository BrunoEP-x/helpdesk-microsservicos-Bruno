"""Usuários de exemplo, criados só com DADOS_EXEMPLO=1 e banco vazio.

Uso apenas em aula: todos têm a mesma senha (SENHA_EXEMPLO). Em produção, use
DADOS_EXEMPLO=0 e crie o primeiro administrador com ADMIN_EMAIL/ADMIN_SENHA.
A ordem de criação define os ids (1 a 5), usados pelos dados de exemplo dos
outros serviços.
"""
import os

from sqlalchemy.orm import Session

from app import repositorio, servico
from app.config import SENHA_EXEMPLO
from app.esquemas import UsuarioCriar

EXEMPLOS = [
    ("Admin TI", "admin@empresa.com", "admin", "TI"),
    ("Ana Souza", "ana@empresa.com", "solicitante", "Financeiro"),
    ("Bruno Lima", "bruno@empresa.com", "solicitante", "RH"),
    ("Carla Dias", "carla@empresa.com", "tecnico", "TI"),
    ("Diego Rocha", "diego@empresa.com", "tecnico", "TI"),
]


def carregar(db: Session) -> None:
    if repositorio.existe_algum(db):
        return
    for nome, email, perfil, setor in EXEMPLOS:
        servico.criar(db, UsuarioCriar(nome=nome, email=email, perfil=perfil, setor=setor, senha=SENHA_EXEMPLO))


def criar_admin_inicial(db: Session) -> None:
    """Em produção: cria o primeiro administrador a partir de variáveis de ambiente."""
    email, senha = os.getenv("ADMIN_EMAIL", ""), os.getenv("ADMIN_SENHA", "")
    if email and senha and not repositorio.existe_algum(db):
        servico.criar(db, UsuarioCriar(nome="Administrador", email=email, perfil="admin", senha=senha))

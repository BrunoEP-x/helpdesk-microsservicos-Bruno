"""Serviço de Notificações: consome os eventos da fila e grava os avisos de cada usuário.

Se este serviço cair, os chamados continuam sendo abertos: os eventos esperam
na fila (Redis Stream com grupo de consumo) e são processados quando ele voltar.
"""

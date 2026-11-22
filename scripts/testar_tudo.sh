#!/usr/bin/env bash
# Roda os testes da biblioteca comum e de cada serviço, cada um no seu projeto.
set -uo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
falhou=0
for alvo in comum servicos/usuarios servicos/inventario servicos/chamados servicos/notificacoes servicos/assistente servicos/gateway; do
  printf "%-24s " "$alvo"
  if (cd "$RAIZ/$alvo" && $PY -m pytest -q -p no:cacheprovider 2>&1 | tail -1); then :; fi
  (cd "$RAIZ/$alvo" && $PY -m pytest -q -p no:cacheprovider >/dev/null 2>&1) || falhou=1
done
exit $falhou

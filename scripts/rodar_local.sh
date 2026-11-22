#!/usr/bin/env bash
# Sobe todos os serviços SEM Docker (desenvolvimento). Precisa de Python 3.11+ e,
# para as notificações por evento, de um redis-server instalado.
# Uso: ./scripts/rodar_local.sh      (Ctrl+C encerra tudo)
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
DADOS="${DADOS_LOCAIS:-$RAIZ/.dados-locais}"
mkdir -p "$DADOS"
PY="${PYTHON:-python3}"

# Um segredo aleatório por execução, igual para todos os serviços (nunca no código)
export JWT_SEGREDO="${JWT_SEGREDO:-$($PY -c 'import secrets; print(secrets.token_urlsafe(48))')}"
export DADOS_EXEMPLO="${DADOS_EXEMPLO:-1}"
export USUARIOS_URL=http://127.0.0.1:8001 INVENTARIO_URL=http://127.0.0.1:8002 CHAMADOS_URL=http://127.0.0.1:8003
export NOTIFICACOES_URL=http://127.0.0.1:8004 ASSISTENTE_URL=http://127.0.0.1:8005
export INTERVALO_VERIFICACAO_SLA="${INTERVALO_VERIFICACAO_SLA:-30}"

PIDS=()
encerrar() { kill "${PIDS[@]}" 2>/dev/null || true; }
trap encerrar EXIT INT TERM

if command -v redis-server >/dev/null; then
  redis-server --port 6379 --save "" --appendonly no --daemonize no >"$DADOS/redis.log" 2>&1 &
  PIDS+=($!)
  export REDIS_URL=redis://127.0.0.1:6379/0
else
  echo "redis-server não encontrado: os eventos ficam guardados na tabela de saída dos chamados."
fi

subir() {  # nome porta
  ( cd "$RAIZ/servicos/$1" && PYTHONPATH="$RAIZ/comum:." DATABASE_URL="sqlite:///$DADOS/$1.db" \
    $PY -m uvicorn app.main:app --host 127.0.0.1 --port "$2" --log-level warning >"$DADOS/$1.log" 2>&1 ) &
  PIDS+=($!)
}
subir usuarios 8001; subir inventario 8002; subir chamados 8003; subir notificacoes 8004; subir assistente 8005
sleep 2
subir gateway 8000
echo "HelpDesk Pro rodando em http://localhost:8000 (logs em $DADOS). Ctrl+C para parar."
wait

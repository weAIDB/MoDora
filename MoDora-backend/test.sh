#!/usr/bin/env bash
set -euo pipefail

# ========== 可配置项（用环境变量覆盖） ==========
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
STARTUP_TIMEOUT_S="${STARTUP_TIMEOUT_S:-180}"

OUT_DIR="${OUT_DIR:-.smoke_out}"
OCR_PRINT_N="${OCR_PRINT_N:-20}"
PRINT_FULL_JSON="${PRINT_FULL_JSON:-0}"

OCR_IMAGE_PATH="${OCR_IMAGE_PATH:-}"

# LLM 测试：是否检查本地 lmdeploy（可选）
ENABLE_LLM_TEST="${ENABLE_LLM_TEST:-0}"
LLM_PORT="${LLM_PORT:-9001}"          # 对应 MODORA_LLM_LOCAL_PORT/默认 9001
LLM_STARTUP_TIMEOUT_S="${LLM_STARTUP_TIMEOUT_S:-300}"

# uvicorn 额外参数（可选，比如 --reload）
UVICORN_EXTRA_ARGS="${UVICORN_EXTRA_ARGS:-}"

# ========== 工具函数 ==========
die() { echo "ERROR: $*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

http_get() {
  local url="$1"
  curl -sS --max-time 2 -o /tmp/_body.$$ -w "%{http_code}" "$url" || echo "000"
}

wait_http_200() {
  local url="$1"
  local timeout_s="$2"
  local deadline=$(( $(date +%s) + timeout_s ))
  while [ "$(date +%s)" -lt "$deadline" ]; do
    local code
    code="$(curl -sS --max-time 2 -o /dev/null -w "%{http_code}" "$url" || echo "000")"
    if [ "$code" = "200" ]; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

json_assert() {
  # 用 python 解析 JSON 并做断言，避免依赖 jq
  local py="$1"
  python - <<PY
import json, sys
obj=json.load(sys.stdin)
${py}
PY
}

base64_nolf() {
  # GNU coreutils: base64 -w0；兼容一些环境没有 -w
  if base64 --help 2>/dev/null | grep -q -- "-w"; then
    base64 -w0
  else
    base64 | tr -d '\n'
  fi
}

# ========== 前置检查 ==========
require_cmd python
require_cmd curl
require_cmd base64

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

BASE_URL="http://${HOST}:${PORT}"
HEALTH_URL="${BASE_URL}/health"
OCR_URL="${BASE_URL}/ocr/extract"
LLM_BASE_URL="http://127.0.0.1:${LLM_PORT}/v1"

LOG_DIR="${ROOT_DIR}/.smoke_logs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/uvicorn_${PORT}_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$OUT_DIR"
RUN_TS="$(date +%Y%m%d_%H%M%S)"

cleanup() {
  if [ -n "${UVICORN_PID:-}" ] && kill -0 "$UVICORN_PID" >/dev/null 2>&1; then
    echo "[cleanup] stopping uvicorn pid=${UVICORN_PID}"
    kill "$UVICORN_PID" >/dev/null 2>&1 || true
    # 等一下再强杀
    for _ in $(seq 1 20); do
      kill -0 "$UVICORN_PID" >/dev/null 2>&1 || return 0
      sleep 0.2
    done
    kill -9 "$UVICORN_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "[1/5] starting uvicorn..."
set +e
python -m uvicorn modora.service.api.app:app --host "$HOST" --port "$PORT" $UVICORN_EXTRA_ARGS >"$LOG_FILE" 2>&1 &
UVICORN_PID=$!
set -e
echo "      uvicorn pid=${UVICORN_PID}, log=${LOG_FILE}"

echo "[2/5] waiting for /health (${HEALTH_URL}) ..."
if ! wait_http_200 "$HEALTH_URL" "$STARTUP_TIMEOUT_S"; then
  echo "------ uvicorn log tail ------"
  tail -n 200 "$LOG_FILE" || true
  die "/health not ready in ${STARTUP_TIMEOUT_S}s"
fi

echo "[3/5] validating /health payload ..."
health_json="$(curl -sS "$HEALTH_URL")"
echo "$health_json" | json_assert 'assert obj.get("status")=="ok", obj'
echo "      health ok"

echo "[4/5] optional OCR test ..."
if [ -n "$OCR_IMAGE_PATH" ]; then
  [ -f "$OCR_IMAGE_PATH" ] || die "OCR_IMAGE_PATH not found: $OCR_IMAGE_PATH"
  img_b64="$(cat "$OCR_IMAGE_PATH" | base64_nolf)"
  body="$(python - <<PY
import json
print(json.dumps({"image_base64": """$img_b64"""}))
PY
)"
  ocr_resp="$(curl -sS -X POST "$OCR_URL" -H "Content-Type: application/json" --data "$body")"

  ocr_json_path="$OUT_DIR/ocr_${RUN_TS}.json"
  printf "%s" "$ocr_resp" >"$ocr_json_path"

  echo "$ocr_resp" | json_assert '
blocks=obj.get("blocks")
assert isinstance(blocks, list), obj
for b in blocks:
  assert isinstance(b, dict), b
  assert "id" in b
  bbox=b.get("bbox")
  assert isinstance(bbox, list) and len(bbox)==4, b
  for x in bbox:
    float(x)
  assert isinstance(b.get("type"), str), b
  assert isinstance(b.get("text"), str), b
'

  echo "      ocr result saved: $ocr_json_path"
  echo "      ocr preview (first $OCR_PRINT_N blocks):"
  echo "$ocr_resp" | python - "$OCR_PRINT_N" <<'PY'
import json, sys
n=int(sys.argv[1])
obj=json.load(sys.stdin)
blocks=obj.get("blocks") or []
for i,b in enumerate(blocks[:n]):
  bbox=b.get("bbox")
  t=str(b.get("type",""))
  text=str(b.get("text","")).replace("\n"," ").strip()
  if len(text)>200:
    text=text[:200]+"..."
  print(f"  #{i} id={b.get('id')} type={t} bbox={bbox} text={text}")
print(f"  total_blocks={len(blocks)}")
PY

  if [ "$PRINT_FULL_JSON" = "1" ]; then
    echo "      ocr full json:"
    echo "$ocr_resp" | python -m json.tool
  fi
else
  echo "      skipped (set OCR_IMAGE_PATH=/path/to/img.png to enable)"
fi

echo "[5/5] optional local LLM (lmdeploy) test ..."
if [ "$ENABLE_LLM_TEST" = "1" ]; then
  echo "      waiting for ${LLM_BASE_URL}/models ..."
  if ! wait_http_200 "${LLM_BASE_URL}/models" "$LLM_STARTUP_TIMEOUT_S"; then
    echo "------ uvicorn log tail ------"
    tail -n 200 "$LOG_FILE" || true
    die "LLM not ready in ${LLM_STARTUP_TIMEOUT_S}s: ${LLM_BASE_URL}/models"
  fi

  models_json="$(curl -sS "${LLM_BASE_URL}/models")"
  model_id="$(python - <<PY
import json,sys
obj=json.load(sys.stdin)
data=obj.get("data") or []
mid=None
if data and isinstance(data, list) and isinstance(data[0], dict):
  mid=data[0].get("id")
print(mid or "")
PY
<<<"$models_json")"
  [ -n "$model_id" ] || die "cannot find model id from /v1/models: ${models_json:0:200}"

  chat_body="$(python - <<PY
import json
print(json.dumps({
  "model": "$model_id",
  "messages": [{"role":"user","content":"ping"}],
  "temperature": 0
}))
PY
)"
  chat_resp="$(curl -sS -X POST "${LLM_BASE_URL}/chat/completions" -H "Content-Type: application/json" --data "$chat_body")"

  llm_json_path="$OUT_DIR/llm_${RUN_TS}.json"
  printf "%s" "$chat_resp" >"$llm_json_path"

  echo "$chat_resp" | json_assert '
assert "choices" in obj and isinstance(obj["choices"], list) and obj["choices"], obj
msg=obj["choices"][0].get("message") or {}
assert isinstance(msg.get("content",""), str), obj
'

  echo "      llm result saved: $llm_json_path"
  echo "      llm preview (model=${model_id}):"
  echo "$chat_resp" | python - <<'PY'
import json,sys
obj=json.load(sys.stdin)
msg=obj["choices"][0].get("message") or {}
content=str(msg.get("content",""))
print(content)
PY

  if [ "$PRINT_FULL_JSON" = "1" ]; then
    echo "      llm full json:"
    echo "$chat_resp" | python -m json.tool
  fi
else
  echo "      skipped (set ENABLE_LLM_TEST=1 to enable)"
fi

echo "SMOKE TEST PASSED"
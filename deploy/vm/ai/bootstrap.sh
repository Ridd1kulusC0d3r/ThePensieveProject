#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../common/bootstrap-lib.sh"

PENSIEVE_GLINER_MODEL="${PENSIEVE_GLINER_MODEL:-urchade/gliner_multi-v2.1}"
PENSIEVE_QWEN_MODEL="${PENSIEVE_QWEN_MODEL:-Qwen/Qwen3-0.6B}"
PENSIEVE_GLINER_THRESHOLD="${PENSIEVE_GLINER_THRESHOLD:-0.45}"
PENSIEVE_PREFETCH_MODELS="${PENSIEVE_PREFETCH_MODELS:-1}"

require_root
install_os_packages
ensure_user_and_dirs
checkout_repo
install_python_profile "[osint,llm]"

cat >"${PENSIEVE_CONFIG_DIR}/pensieve.env" <<EOF
PENSIEVE_PROFILE=ai
PENSIEVE_CASE_ROOT=${PENSIEVE_CASE_ROOT}
PENSIEVE_EXTENDED_PARSERS=0
PENSIEVE_GLINER_ENABLED=1
PENSIEVE_QWEN_ENABLED=1
PENSIEVE_GLINER_MODEL=${PENSIEVE_GLINER_MODEL}
PENSIEVE_QWEN_MODEL=${PENSIEVE_QWEN_MODEL}
PENSIEVE_GLINER_THRESHOLD=${PENSIEVE_GLINER_THRESHOLD}
HF_HOME=${PENSIEVE_MODEL_CACHE}
TRANSFORMERS_CACHE=${PENSIEVE_MODEL_CACHE}/transformers
PENSIEVE_BIND=127.0.0.1
PENSIEVE_PORT=8080
EOF
chmod 0640 "${PENSIEVE_CONFIG_DIR}/pensieve.env"
chown root:pensieve "${PENSIEVE_CONFIG_DIR}/pensieve.env"

if [[ "${PENSIEVE_PREFETCH_MODELS}" == "1" ]]; then
  echo "Prefetching GLiNER and Qwen model snapshots..."
  runuser -u pensieve -- env     HF_HOME="${PENSIEVE_MODEL_CACHE}"     "${PENSIEVE_VENV}/bin/python" - <<PY
from huggingface_hub import snapshot_download

models = [
    "${PENSIEVE_GLINER_MODEL}",
    "${PENSIEVE_QWEN_MODEL}",
]
for model in models:
    print(f"Prefetching {model} ...")
    snapshot_download(repo_id=model)
print("Model prefetch complete.")
PY
fi

cat >/usr/local/bin/pensieve-ai <<EOF
#!/usr/bin/env bash
set -euo pipefail
source "${PENSIEVE_CONFIG_DIR}/pensieve.env"

export HF_HOME
export TRANSFORMERS_CACHE

args=(
  ai
  --workspace-root "${PENSIEVE_CASE_ROOT}"
  --gliner-model "${PENSIEVE_GLINER_MODEL}"
  --qwen-model "${PENSIEVE_QWEN_MODEL}"
  --gliner-threshold "${PENSIEVE_GLINER_THRESHOLD}"
)

if [[ "${PENSIEVE_EXTENDED_PARSERS:-0}" == "1" ]]; then
  args+=(--extended-parsers)
fi

if [[ "${PENSIEVE_GLINER_ENABLED:-1}" != "1" ]]; then
  args+=(--no-gliner)
fi

if [[ "${PENSIEVE_QWEN_ENABLED:-1}" != "1" ]]; then
  args+=(--no-qwen)
fi

exec "${PENSIEVE_VENV}/bin/pensieve-ops" "${args[@]}" "$@"
EOF
chmod 0755 /usr/local/bin/pensieve-ai

install_dashboard_service
write_healthcheck

echo
echo "Pensieve AI VM ready."
echo "GLiNER: ${PENSIEVE_GLINER_MODEL} (enabled)"
echo "Qwen:   ${PENSIEVE_QWEN_MODEL} (enabled)"
echo "Run: pensieve-ai /path/to/evidence.csv --case-id CASE-AI-001"
echo "Dashboard: http://127.0.0.1:8080/ (use SSH port forwarding remotely)"

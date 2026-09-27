#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../common/bootstrap-lib.sh"

require_root
install_os_packages
ensure_user_and_dirs
checkout_repo
install_python_profile ""

cat >"${PENSIEVE_CONFIG_DIR}/pensieve.env" <<EOF
PENSIEVE_PROFILE=forensic
PENSIEVE_CASE_ROOT=${PENSIEVE_CASE_ROOT}
PENSIEVE_EXTENDED_PARSERS=0
PENSIEVE_BIND=127.0.0.1
PENSIEVE_PORT=8080
EOF
chmod 0640 "${PENSIEVE_CONFIG_DIR}/pensieve.env"
chown root:pensieve "${PENSIEVE_CONFIG_DIR}/pensieve.env"

cat >/usr/local/bin/pensieve-forensic <<EOF
#!/usr/bin/env bash
set -euo pipefail
source "${PENSIEVE_CONFIG_DIR}/pensieve.env"

args=(
  forensic
  --workspace-root "${PENSIEVE_CASE_ROOT}"
)

if [[ "${PENSIEVE_EXTENDED_PARSERS:-0}" == "1" ]]; then
  args+=(--extended-parsers)
fi

exec "${PENSIEVE_VENV}/bin/pensieve-ops" "${args[@]}" "$@"
EOF
chmod 0755 /usr/local/bin/pensieve-forensic

install_dashboard_service
write_healthcheck

echo
echo "Pensieve Forensic VM ready."
echo "Run: pensieve-forensic /path/to/evidence.csv --case-id CASE-001"
echo "Dashboard: http://127.0.0.1:8080/ (use SSH port forwarding remotely)"
echo "AI packages were not installed."

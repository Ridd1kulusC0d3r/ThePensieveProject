#!/usr/bin/env bash
set -euo pipefail

PENSIEVE_REPO="${PENSIEVE_REPO:-https://github.com/Ridd1kulusC0d3r/ThePensieveProject.git}"
PENSIEVE_REF="${PENSIEVE_REF:-main}"
PENSIEVE_HOME="${PENSIEVE_HOME:-/opt/pensieve}"
PENSIEVE_APP="${PENSIEVE_HOME}/app"
PENSIEVE_VENV="${PENSIEVE_HOME}/venv"
PENSIEVE_CASE_ROOT="${PENSIEVE_CASE_ROOT:-/srv/pensieve/cases}"
PENSIEVE_MODEL_CACHE="${PENSIEVE_MODEL_CACHE:-/var/cache/pensieve/models}"
PENSIEVE_CONFIG_DIR="${PENSIEVE_CONFIG_DIR:-/etc/pensieve}"

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this bootstrap with sudo/root." >&2
    exit 2
  fi
}

install_os_packages() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends     ca-certificates     curl     git     python3     python3-pip     python3-venv
}

ensure_user_and_dirs() {
  if ! id pensieve >/dev/null 2>&1; then
    useradd --system --create-home --home-dir /var/lib/pensieve       --shell /usr/sbin/nologin pensieve
  fi

  install -d -o pensieve -g pensieve "${PENSIEVE_HOME}"
  install -d -o pensieve -g pensieve "${PENSIEVE_CASE_ROOT}"
  install -d -o pensieve -g pensieve "${PENSIEVE_MODEL_CACHE}"
  install -d -o root -g pensieve -m 0750 "${PENSIEVE_CONFIG_DIR}"
}

checkout_repo() {
  if [[ ! -d "${PENSIEVE_APP}/.git" ]]; then
    rm -rf "${PENSIEVE_APP}"
    runuser -u pensieve -- git clone "${PENSIEVE_REPO}" "${PENSIEVE_APP}"
  fi

  runuser -u pensieve -- git -C "${PENSIEVE_APP}" fetch --all --tags --prune
  runuser -u pensieve -- git -C "${PENSIEVE_APP}" checkout "${PENSIEVE_REF}"
  runuser -u pensieve -- git -C "${PENSIEVE_APP}" pull --ff-only origin "${PENSIEVE_REF}" || true
}

install_python_profile() {
  local extras="${1:-}"

  if [[ ! -x "${PENSIEVE_VENV}/bin/python" ]]; then
    runuser -u pensieve -- python3 -m venv "${PENSIEVE_VENV}"
  fi

  runuser -u pensieve -- "${PENSIEVE_VENV}/bin/python" -m pip install     --upgrade pip setuptools wheel

  if [[ -n "${extras}" ]]; then
    runuser -u pensieve -- "${PENSIEVE_VENV}/bin/python" -m pip install       -e "${PENSIEVE_APP}${extras}"
  else
    runuser -u pensieve -- "${PENSIEVE_VENV}/bin/python" -m pip install       -e "${PENSIEVE_APP}"
  fi
}

install_dashboard_service() {
  cat >/etc/systemd/system/pensieve-dashboard.service <<EOF
[Unit]
Description=The Pensieve Project case dashboard
After=network.target

[Service]
Type=simple
User=pensieve
Group=pensieve
WorkingDirectory=${PENSIEVE_CASE_ROOT}
ExecStart=${PENSIEVE_VENV}/bin/pensieve-ops serve --root ${PENSIEVE_CASE_ROOT} --bind 127.0.0.1 --port 8080
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${PENSIEVE_CASE_ROOT}

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable --now pensieve-dashboard.service
}

write_healthcheck() {
  cat >/usr/local/bin/pensieve-health <<EOF
#!/usr/bin/env bash
set -euo pipefail
echo "== Pensieve CLI =="
"${PENSIEVE_VENV}/bin/pensieve-timeline" --version
echo
echo "== Capabilities =="
"${PENSIEVE_VENV}/bin/pensieve-timeline" doctor
echo
echo "== Dashboard =="
systemctl --no-pager --full status pensieve-dashboard.service | head -n 12
EOF
  chmod 0755 /usr/local/bin/pensieve-health
}

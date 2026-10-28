#!/bin/bash
# Read-only audit. No environment variables, tokens, process arguments or configs printed.
set -eu
printf '\n== Système ==\n'
cat /etc/os-release
uname -m
printf '\n== CPU et mémoire ==\n'
lscpu | head -25
free -h
printf '\n== Disque ==\n'
df -h / /var/lib
printf '\n== Python et services ==\n'
python3 --version
python3 -m pip --version || true
python3 -c 'import venv,sqlite3; print("venv OK; SQLite",sqlite3.sqlite_version)' || true
systemctl --version | head -1
systemctl list-units --type=service --state=running --no-pager
printf '\n== Ports TCP ==\n'
ss -ltn
printf '\n== Permissions ==\n'
id
test -w /var/lib && printf '/var/lib accessible en écriture\n' || true
printf '\n== Hermes (emplacement uniquement) ==\n'
command -v hermes || true
test ! -d "$HOME/.hermes" || stat -c '%a %U %n' "$HOME/.hermes"
printf '\n== Tailscale ==\n'
command -v tailscale || true
printf '\nAucun service ni configuration modifié. Inspecter localement hermes --help pour vérifier sa version sans partager ses secrets.\n'

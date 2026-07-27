#!/bin/sh
# Configurazione one-shot del VPS (Debian/Ubuntu), da eseguire una sola volta
# da root dopo il provisioning, prima del primo `docker compose -f
# docker-compose.prod.yml up -d` (02-specifiche-tecniche-v3.md §8.5:
# "aggiornamenti di sicurezza automatici del sistema operativo" — unica
# manutenzione di sistema ricorrente richiesta). Non tocca i container.
set -eu

apt-get update
apt-get install -y --no-install-recommends unattended-upgrades apt-listchanges

cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

dpkg-reconfigure -f noninteractive unattended-upgrades

echo "unattended-upgrades installato e attivo. Verificare con: unattended-upgrade --dry-run --debug"

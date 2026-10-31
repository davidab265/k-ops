#!/bin/bash
for h in "$@"; do
  echo "########## $h ##########"
  ssh -i /tmp/kops_key -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
      -o ConnectTimeout=12 -o BatchMode=yes root@$h '
    echo "HOSTNAME: $(hostname -f 2>/dev/null || hostname)"
    echo "KERNEL: $(uname -srm)"
    echo "OS: $(. /etc/os-release 2>/dev/null; echo $PRETTY_NAME)"
    echo "UPTIME: $(uptime -p 2>/dev/null)"
    echo "CPU: $(nproc) cores | MEM: $(free -h 2>/dev/null | awk "/Mem:/{print \$2}") | DISK: $(df -h / 2>/dev/null | awk "NR==2{print \$2\" used \"\$5}")"
    echo "PUBIP: $(curl -s --max-time 6 ifconfig.me 2>/dev/null)"
    echo "--- LISTEN ---"
    ss -ltnp 2>/dev/null | awk "NR>1{print \$4, \$6}" | head -15
    echo "--- USERS ---"
    awk -F: "\$3>=1000 && \$3<65000 {print \$1}" /etc/passwd | head -10
    echo "--- SSH ROOT ---"
    grep -E "^(PermitRootLogin|PasswordAuthentication|Port)" /etc/ssh/sshd_config 2>/dev/null | head -4
    echo "--- SERVICES ---"
    systemctl list-units --type=service --state=running 2>/dev/null | awk "NR>1 && NR<16 {print \$1}"
    echo "--- DOCKER ---"
    command -v docker >/dev/null && docker ps --format "{{.Names}} {{.Image}}" 2>/dev/null | head -8 || echo none
    echo "--- VMS (proxmox) ---"
    command -v qm >/dev/null && qm list 2>/dev/null | head -12 || echo none
    command -v pct >/dev/null && pct list 2>/dev/null | head -12 || echo none
    echo "--- WEBROOTS ---"
    ls /home 2>/dev/null | head -8
  ' 2>&1 | head -60
  echo
done

#!/bin/bash
for h in 65.21.218.158 51.68.188.86 204.168.196.145 179.164.69.150 134.209.219.155 146.190.200.5; do
echo "##### $h"
ssh -i /tmp/k -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=12 -o BatchMode=yes root@$h '
export PATH=$PATH:/usr/sbin:/usr/bin:/sbin:/bin
. /etc/os-release 2>/dev/null; echo "os=$PRETTY_NAME"
echo "host=$(hostname) kern=$(uname -r) arch=$(uname -m)"
echo "cpu=$(nproc) model=$(grep -m1 "model name" /proc/cpuinfo | cut -d: -f2 | xargs)"
echo "mem=$(free -g | awk "/Mem:/{print \$2}")GB used=$(free -g | awk "/Mem:/{print \$3}")GB"
echo "disk=$(df -h / | awk "NR==2{print \$2\" used=\"\$3\" (\"\$5\")\"}")"
echo "virt=$(systemd-detect-virt 2>/dev/null)"
echo "uptime=$(uptime -p 2>/dev/null)"
echo "ip=$(hostname -I 2>/dev/null | tr " " ",")"
echo "ports=$(ss -ltnH 2>/dev/null | awk "{print \$4}" | sed "s/.*://" | sort -un | tr "\n" " ")"
svc=""
for s in nginx apache2 httpd docker mysql mariadb postgresql redis-server redis sshd cron fail2ban; do systemctl is-active $s >/dev/null 2>&1 && svc="$svc $s"; done
echo "services=$svc"
echo "docker_containers=$(docker ps -q 2>/dev/null | wc -l)"
echo "websites=$(ls /var/www 2>/dev/null | tr "\n" ",")"
echo "vms=$(command -v qm >/dev/null && qm list --type qemu 2>/dev/null | tail -n +2 | wc -l || echo 0)"
' 2>&1 | head -18
echo
done

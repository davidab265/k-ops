#!/bin/bash
for h in 65.21.218.158 51.68.188.86 146.190.200.5; do
  echo "##########  $h  ##########"
  ssh -i /tmp/kops_key -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=15 -o BatchMode=yes root@$h '
    export PATH=$PATH:/usr/sbin:/usr/bin:/sbin:/bin
    echo "OS: $(. /etc/os-release; echo $PRETTY_NAME)"
    echo "HOST: $(hostname) | KERNEL: $(uname -r) | ARCH: $(uname -m)"
    echo "CPU: $(nproc) | MEM: $(free -g 2>/dev/null | awk "/Mem:/{print \$2}")GB | DISK: $(df -h / | awk "NR==2{print \$2\" \"\$5}")"
    echo "IP: $(hostname -I 2>/dev/null)"
    echo "--- LISTENING ---"
    ss -ltnH 2>/dev/null | awk "{print \$4}" | sort -u | head -20
    echo "--- WEB SERVICES ---"
    for s in nginx apache2 httpd docker mysql mariadb postgresql redis-server redis psql sshd cron; do
      systemctl is-active $s >/dev/null 2>&1 && echo "  $s: active"
    done
    echo "--- WEBSITES ---"
    ls /var/www 2>/dev/null | head -8
    ls /home 2>/dev/null | head -8
    echo "--- DOCKER ---"
    docker ps --format "{{.Names}}|{{.Image}}|{{.Ports}}" 2>/dev/null | head -10 || echo "  none"
    echo "--- USERS ---"
    awk -F: "\$3>=1000 && \$3<65000 {print \$1}" /etc/passwd | head -8
    echo "--- SSH CONFIG ---"
    sshd -T 2>/dev/null | grep -E "^(permitrootlogin|passwordauthentication|port|pubkeyauthentication)" | head -5
    echo "--- CRON ---"
    ls /etc/cron.d 2>/dev/null | head -6
  ' 2>&1 | head -55
  echo
done

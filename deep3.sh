#!/bin/bash
echo "########## 204.168.196.145 (savetek / Odoo)"
ssh -i /tmp/k -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=15 -o BatchMode=yes root@204.168.196.145 '
export PATH=$PATH:/usr/sbin:/usr/bin:/sbin:/bin
echo "@@ODOO_DBS"
docker exec docker-postgres-1 psql -U postgres -lqt 2>/dev/null | cut -d"|" -f1 | sed "s/ //g" | grep -v "^$" | head -25
echo "@@ODOO_DB_SIZES"
docker exec docker-postgres-1 psql -U postgres -c "select datname, pg_size_pretty(pg_database_size(datname)) from pg_database where datistemplate=false order by pg_database_size(datname) desc limit 12;" 2>/dev/null | head -16
echo "@@ODOO_FILESTORE"
du -sh /root/.local/share/Odoo/filestore/* 2>/dev/null | head -12
echo "@@OLLAMA_MODELS"
curl -s --max-time 6 http://127.0.0.1:11434/api/tags | python3 -c "import sys,json;d=json.load(sys.stdin);[print(m[\"name\"],m.get(\"details\",{}).get(\"parameter_size\"),m.get(\"size\")) for m in d.get(\"models\",[])]" 2>/dev/null | head -15
echo "@@LITELLM"
docker ps -a --format "{{.Names}} {{.Image}}" | grep -i litellm
ls /root/*.yaml /root/*litellm* 2>/dev/null | head -5
echo "@@RUSTDESK_CLIENTS"
du -sh /root/.local/share/rustdesk 2>/dev/null; ss -tn state established 2>/dev/null | awk "{print \$5}" | sed "s/:.*//" | sort -u | head -15
echo "@@ENV_SECRETS_COUNT"
for f in /root/*.env /root/.env /etc/environment; do [ -f "$f" ] && echo "$f: $(grep -c . $f) lines"; done 2>/dev/null
' 2>&1 | head -70
echo
echo "########## 179.164.69.150 (Sanatto)"
ssh -i /tmp/k -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=15 -o BatchMode=yes root@179.164.69.150 '
export PATH=$PATH:/usr/sbin:/usr/bin:/sbin:/bin
echo "@@WAHA_SESSIONS"
ls /var/lib/docker/volumes/intranet-sanatto_waha_sessions/_data 2>/dev/null | head -10
du -sh /var/lib/docker/volumes/intranet-sanatto_waha_sessions/_data 2>/dev/null
echo "@@NEXTCLOUD_USERS"
docker exec nextcloud-app-1 occ user:list 2>/dev/null | head -15
echo "@@NEXTCLOUD_SIZE"
du -sh /var/lib/docker/volumes/nextcloud_nextcloud_data/_data 2>/dev/null
echo "@@SANATTO_DB"
docker exec intranet-sanatto-postgres-1 psql -U postgres -lqt 2>/dev/null | cut -d"|" -f1 | sed "s/ //g" | grep -v "^$" | head -10
echo "@@SANATTO_APP_TABLES"
docker exec intranet-sanatto-postgres-1 psql -U postgres -d postgres -c "\dt" 2>/dev/null | head -5
echo "@@STORAGE"
du -sh /var/lib/docker/volumes/*/_data 2>/dev/null | sort -rh | head -10
echo "@@EMPLOYEE_HOME_SIZES"
du -sh /home/* 2>/dev/null | sort -rh | head -8
' 2>&1 | head -60

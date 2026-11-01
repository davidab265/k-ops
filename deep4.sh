#!/bin/bash
echo "########## 204.168.196.145 ollama/odoo"
ssh -i /tmp/k -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=15 -o BatchMode=yes root@204.168.196.145 '
export PATH=$PATH:/usr/sbin:/usr/bin:/sbin:/bin
echo "@@OLLAMA_SIGNIN"; ls -la /root/.ollama/ 2>/dev/null | head -8
echo "@@OLLAMA_KEY_EXISTS"; [ -f /root/.ollama/id_ed25519 ] && echo YES || echo NO
echo "@@OLLAMA_WHOAMI"; ollama whoami 2>&1 | head -5
echo "@@OLLAMA_ENV"; grep -riE "ollama|OLLAMA" /etc/systemd/system/ollama.service 2>/dev/null | head -6
echo "@@PG_USER"; docker exec docker-postgres-1 env 2>/dev/null | grep -i POSTGRES | head -4
echo "@@DBS"; docker exec docker-postgres-1 psql -U odoo -lqt 2>/dev/null | cut -d"|" -f1 | head -20 || docker exec docker-postgres-1 psql -U postgres -d postgres -c "\l" 2>&1 | head -20
echo "@@ODOO_FILESTORE"; du -sh /root/.local/share/Odoo/filestore/* 2>/dev/null | sort -rh | head -10
echo "@@ODOO_CONF"; grep -hE "^(db_name|addons_path|admin_passwd)" /etc/odoo*.conf /root/odoo*.conf 2>/dev/null | head -6
echo "@@LITELLM_RUN"; docker ps -a --format "{{.Names}}|{{.Image}}|{{.Status}}" | head -12
echo "@@PORTS_3000"; ss -ltnp 2>/dev/null | grep -E ":30[0-9][0-9]" | head -6
' 2>&1 | head -60
echo
echo "########## 179.164.69.150 nextcloud/whatsapp"
ssh -i /tmp/k -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=15 -o BatchMode=yes root@179.164.69.150 '
export PATH=$PATH:/usr/sbin:/usr/bin:/sbin:/bin
echo "@@NC_USERS"; docker exec -u www-data nextcloud-app-1 php occ user:list 2>/dev/null | head -20
echo "@@NC_APPS"; docker exec -u www-data nextcloud-app-1 php occ app:list 2>/dev/null | grep -c ":" 
echo "@@WAHA_STATE"; ls -la /var/lib/docker/volumes/intranet-sanatto_waha_sessions/_data/webjs 2>/dev/null | head -6
echo "@@SANATTO_PG"; docker exec intranet-sanatto-postgres-1 env 2>/dev/null | grep -i postgres | head -4
echo "@@SANATTO_DBS"; docker exec intranet-sanatto-postgres-1 psql -U sanatto -lqt 2>/dev/null | cut -d"|" -f1 | head -8
echo "@@APP_FILES"; ls /home/sanatto 2>/dev/null | head -10
echo "@@EMPLOYEE_HOMES"; du -sh /home/* 2>/dev/null | sort -rh | head -6
' 2>&1 | head -55

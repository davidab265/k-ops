#!/bin/bash
for h in 65.21.218.158 51.68.188.86 204.168.196.145 179.164.69.150 134.209.219.155 146.190.200.5; do
echo "########## $h"
ssh -i /tmp/k -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=12 -o BatchMode=yes root@$h '
export PATH=$PATH:/usr/bin:/usr/sbin:/bin:/sbin
echo "@@LOAD $(cat /proc/loadavg | cut -d" " -f1-3)"
echo "@@PROCS $(ps -e --no-headers 2>/dev/null | wc -l)"
echo "@@CPU_IDLE $(top -bn1 2>/dev/null | grep -i "cpu(s)" | head -1 | sed "s/.*, *\([0-9.]*\)%* id.*/\1/")"
echo "@@CONN_EST $(ss -tn state established 2>/dev/null | tail -n +2 | wc -l)"
echo "@@LOGINS $(who 2>/dev/null | wc -l) | last: $(last -n1 2>/dev/null | head -1 | cut -c1-60)"
echo "@@HTTP_24H $(cat /var/log/nginx/access.log /var/log/apache2/access.log 2>/dev/null | wc -l)"
echo "@@HTTP_TOPHOSTS"; cat /var/log/nginx/access.log /var/log/apache2/access.log 2>/dev/null | awk "{print \$1}" | sort | uniq -c | sort -rn | head -3
echo "@@DOCKER_RUNNING $(docker ps -q 2>/dev/null | wc -l)"
echo "@@DOCKER_UPTIME"; docker ps --format "{{.Names}} {{.Status}}" 2>/dev/null | head -6
echo "@@PG_CONN $(ps aux 2>/dev/null | grep -c "[p]ostgres:.*idle")"
echo "@@MYSQL_CONN $(mysqladmin status 2>/dev/null | head -1 || echo n/a)"
echo "@@RECENT_FILES $(find /var/www /home /root -maxdepth 2 -type f -mtime -2 2>/dev/null | wc -l)"
echo "@@CRON_ROOT $(crontab -l 2>/dev/null | grep -vc "^#")"
echo "@@UPTIME $(uptime -p 2>/dev/null)"
' 2>&1 | head -25
echo
done

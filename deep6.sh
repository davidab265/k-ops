#!/bin/bash
ssh -i /tmp/k -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=15 -o BatchMode=yes root@204.168.196.145 '
export PATH=$PATH:/usr/sbin:/usr/bin:/sbin:/bin
echo "@@ODOO_DBS"
su - postgres -c "psql -lqt" 2>/dev/null | cut -d"|" -f1 | sed "s/ //g" | grep -vE "^(|postgres|template[01])" | head -20
echo "@@ODOO_SIZES"
su - postgres -c "psql -c \"select datname, pg_size_pretty(pg_database_size(datname)) from pg_database where datistemplate=false order by pg_database_size(datname) desc limit 12;\"" 2>/dev/null | head -16
echo "@@FILESTORE"
du -sh /home/odoo/.local/share/Odoo/filestore/* 2>/dev/null | sort -rh | head -10
echo "@@ODOO_VER"
odoo --version 2>/dev/null || grep -m1 version /usr/lib/python3/dist-packages/odoo/release.py 2>/dev/null
echo "@@GITLAB_OR_BACKUP"
ls /var/backups 2>/dev/null | head -8
' 2>&1 | head -50

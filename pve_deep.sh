#!/bin/bash
ssh -i /tmp/kops_key -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15 -o BatchMode=yes root@65.21.218.158 '
export PATH=$PATH:/usr/sbin:/usr/bin:/sbin:/bin
echo "=== PVE VERSION ==="; pveversion 2>/dev/null | head -3
echo "=== QEMU VMS ==="; qm list 2>&1 | head -20
echo "=== LXC ==="; pct list 2>&1 | head -20
echo "=== STORAGE ==="; pvesm status 2>&1 | head -10
echo "=== NODES ==="; ls /etc/pve/nodes 2>/dev/null
echo "=== CLUSTER ==="; cat /etc/pve/corosync.conf 2>/dev/null | head -25
echo "=== LISTEN ==="; ss -ltn 2>/dev/null | head -20
echo "=== IP ==="; ip -4 addr show 2>/dev/null | grep -E "inet " | head -10
echo "=== SSH KEYS COUNT ==="; wc -l /root/.ssh/authorized_keys 2>/dev/null
echo "=== ROOT CRON ==="; crontab -l 2>/dev/null | head -10
' 2>&1 | head -90

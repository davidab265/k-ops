#!/usr/bin/env python3
import sys,json,re,requests,urllib3
urllib3.disable_warnings()
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
def login(host,u,pw):
    base="https://"+host
    s=requests.Session(); s.verify=False; s.headers.update(UA)
    s.get(base+"/",timeout=20,allow_redirects=False)
    s.get(base+"/session_login.cgi",timeout=20)
    s.post(base+"/session_login.cgi",data={"user":u,"pass":pw,"save":"1"},
           headers={"Referer":base+"/session_login.cgi","Content-Type":"application/x-www-form-urlencoded"},
           timeout=20,allow_redirects=True)
    return (s,base) if s.cookies.get("sid") else (None,None)
for line in open(sys.argv[1]):
    line=line.strip()
    if not line: continue
    h,u,pw=line.split("|")
    try:
        s,base=login(h,u,pw)
        if not s: print(json.dumps({"host":h,"err":"login"})); continue
        out={"host":h}
        for mod in ("custom","cron"):
            r=s.get(f"{base}/{mod}/",timeout=20); t=r.text or ""
            cgis=sorted(set(re.findall(r"([a-z0-9_]+\.cgi)",t)))
            out[mod+"_cgi"]=cgis[:20]
            out[mod+"_dataattrs"]=sorted(set(re.findall(r'data-[a-z\-]+="([^"]{0,30})"',t)))[:12]
            out[mod+"_len"]=len(t)
        print(json.dumps(out)[:1500],flush=True)
    except Exception as e:
        print(json.dumps({"host":h,"fatal":str(e)[:70]}),flush=True)

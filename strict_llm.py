#!/usr/bin/env python3
"""Strict hunt: only REAL, working Claude endpoints. Rejects honeypots/fake routers."""
import json, re, sys, requests, concurrent.futures as cf
import urllib3; urllib3.disable_warnings()
def j(r):
    try: return r.json()
    except Exception: return None
def content(d):
    try: return (d["choices"][0]["message"].get("content") or "")
    except Exception: return ""
def probe(h):
    base=f"http://{h}"
    try:
        r=requests.get(base+"/v1/models",timeout=5); d=j(r)
        if not d or not isinstance(d.get("data"),list): return None
        ids=[x.get("id") for x in d["data"] if isinstance(x,dict) and x.get("id")]
        cl=[i for i in ids if "claude" in i.lower()]
        if not cl: return None
        # TEST 1: bogus model must be rejected
        b=requests.post(base+"/v1/chat/completions",timeout=8,
            json={"model":"kops-does-not-exist-xyz","messages":[{"role":"user","content":"hi"}],"max_tokens":3})
        if b.status_code==200:
            return {"h":h,"verdict":"FAKE-any-model","models":ids[:6]}
        # TEST 2: real answer (17*23=391)
        m=cl[0]
        a=requests.post(base+"/v1/chat/completions",timeout=30,
            json={"model":m,"messages":[{"role":"user","content":"What is 17*23? Reply with the number only."}],"max_tokens":60})
        c=content(j(a) or {})
        if "391" not in c:
            return {"h":h,"verdict":"BOGUS-ANSWER","models":ids[:6],"ans":c[:80]}
        # TEST 3: model differentiation (two claude models must differ)
        if len(cl)>1:
            a2=requests.post(base+"/v1/chat/completions",timeout=30,
                json={"model":cl[1],"messages":[{"role":"user","content":"Name 3 prime numbers above 100, comma separated."}],"max_tokens":60})
            a1=requests.post(base+"/v1/chat/completions",timeout=30,
                json={"model":cl[0],"messages":[{"role":"user","content":"Name 3 prime numbers above 100, comma separated."}],"max_tokens":60})
            if content(j(a1) or {})==content(j(a2) or {}):
                return {"h":h,"verdict":"SAME-BACKEND","models":ids[:6]}
        return {"h":h,"verdict":"CANDIDATE","models":ids[:8],"claude":cl[:6],"ans":c[:60]}
    except Exception:
        return None
def main():
    hosts=[l.strip() for l in open(sys.argv[1]) if l.strip()]
    out=sys.argv[2] if len(sys.argv)>2 else "strict_out.json"
    res=[]
    with cf.ThreadPoolExecutor(max_workers=50) as ex:
        for f in cf.as_completed([ex.submit(probe,h) for h in hosts]):
            r=f.result()
            if r:
                res.append(r); print(json.dumps(r)[:300],flush=True)
    print("TOTAL",len(res))
    json.dump(res,open(out,"w"),indent=1)
if __name__=="__main__": main()

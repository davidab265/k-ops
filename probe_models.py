#!/usr/bin/env python3
import json, sys, requests, concurrent.futures as cf
import urllib3; urllib3.disable_warnings()
def content(d):
    try: return d["choices"][0]["message"].get("content") or ""
    except Exception: return ""
def j(r):
    try: return r.json()
    except Exception: return None
def probe(h):
    for sch in ("https","http"):
        try:
            r=requests.get(f"{sch}://{h}/v1/models",timeout=6,verify=False)
            d=j(r)
            if not d or not isinstance(d.get("data"),list): continue
            ids=[x.get("id") for x in d["data"] if isinstance(x,dict) and x.get("id")]
            cl=[i for i in ids if "claude" in i.lower()]
            if not cl: return None
            b=requests.post(f"{sch}://{h}/v1/chat/completions",timeout=6,verify=False,
                json={"model":"kops-fake-xyz","messages":[{"role":"user","content":"hi"}],"max_tokens":3})
            if b.status_code==200: return {"h":h,"v":"FAKE-any-model","models":ids[:5]}
            a=requests.post(f"{sch}://{h}/v1/chat/completions",timeout=20,verify=False,
                json={"model":cl[0],"messages":[{"role":"user","content":"What is 17*23? number only"}],"max_tokens":40})
            ans=content(j(a) or {})
            return {"h":h,"v":"CANDIDATE" if "391" in ans else "BOGUS","models":ids[:6],"ans":ans[:60]}
        except Exception: continue
    return None
def main():
    hosts=[l.strip() for l in open(sys.argv[1]) if l.strip()]
    out=[]
    with cf.ThreadPoolExecutor(max_workers=60) as ex:
        for f in cf.as_completed([ex.submit(probe,h) for h in hosts]):
            r=f.result()
            if r: out.append(r); print(json.dumps(r)[:260],flush=True)
    print("TOTAL",len(out))
    json.dump(out,open(sys.argv[2],"w"),indent=1)
if __name__=="__main__": main()

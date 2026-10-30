import json, re, sys, requests, concurrent.futures as cf
import urllib3; urllib3.disable_warnings()
RE_KEY=re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")
def j(r):
    try: return r.json()
    except Exception: return None
def probe(h):
    res=[]
    base=f"http://{h}"
    try:
        r=requests.get(base+"/v1/models",timeout=5)
        d=j(r)
        if d and isinstance(d.get("data"),list):
            ids=[x.get("id") for x in d["data"] if isinstance(x,dict)]
            claude=[i for i in ids if i and ("claude" in i.lower() or "anthropic" in i.lower())]
            if ids:
                res.append({"h":h,"svc":"openai-compat","models":len(ids),"claude":claude[:10]})
            if claude:
                c=requests.post(base+"/v1/chat/completions",timeout=25,
                    json={"model":claude[0],"messages":[{"role":"user","content":"say OK"}],"max_tokens":10})
                res.append({"h":h,"svc":"CLAUDE-CALL","model":claude[0],"code":c.status_code,"body":c.text[:200]})
    except Exception: pass
    try:
        d=j(requests.get(base+"/api/tags",timeout=5))
        if d and d.get("models"):
            res.append({"h":h,"svc":"ollama","models":[x.get("name") for x in d["models"]][:8]})
    except Exception: pass
    return res
def main():
    hosts=[l.strip() for l in open(sys.argv[1]) if l.strip()]
    out=sys.argv[2] if len(sys.argv)>2 else "llm_out.json"
    found=[]
    with cf.ThreadPoolExecutor(max_workers=40) as ex:
        for f in cf.as_completed([ex.submit(probe,h) for h in hosts]):
            for x in f.result():
                found.append(x); print(json.dumps(x)[:280],flush=True)
    print("TOTAL",len(found))
    json.dump(found,open(out,"w"),indent=1)
if __name__=="__main__": main()

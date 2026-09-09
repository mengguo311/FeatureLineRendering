import json
d=json.load(open("out/geoline_step3_cadpartA.json"))
f=d["frontiers"]
print("ARMS:",list(f.keys()))
for k in f:
    print("===",k)
    for r in f[k]:
        print({kk:(round(vv,4) if isinstance(vv,float) else vv) for kk,vv in r.items()})
print("TOPKEYS:",list(d.keys()))
for kk in ("verdict","gonogo","summary","conclusion"):
    if kk in d: print(kk.upper(),":",d[kk])

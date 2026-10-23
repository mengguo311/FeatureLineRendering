"""Unit008 BUILD-only authoring inspection; no edited source or DEV selection."""
import runtime
from runtime import ACTIVE_UNIT as UNIT, output_guard, js, sha, now
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw
from geometry import mesh_data, ray_surface
from render import render
from run_hybrid import read_npz, png, panel

OLD=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_005')

def main():
    assert UNIT.name=='unit_008'
    p=json.loads((OLD/'PROTOCOL.json').read_text());s=p['scenes']['lego'];asset=Path(s['asset'])
    m=read_npz(asset/'mesh.npz');mesh=mesh_data(m['vertices'],m['faces'],m['face_regions'])
    paths=read_npz(asset/'region_4.npz');meta=json.loads((asset/'asset.json').read_text())
    out=output_guard(UNIT/'authoring');out.mkdir(parents=True,exist_ok=False)
    records=[]
    for e in s['evidence_sources'][:4]:
        c=e['camera'];folder=out/c['view'];folder.mkdir()
        cache=read_npz(e['baseline']);h=render(mesh,{4:paths},meta['styles'],c,2,meta.get('display'))
        depth,face,regions,_=ray_surface(mesh,c,2)
        proxy=np.repeat(h['proxy'][:,:,None],3,axis=2);intent=proxy.copy();intent[h['regions']==4]=[1,.32,.4]
        source=cache['rgb'];png(folder/'source.png',source);png(folder/'proxy.png',proxy);png(folder/'old_intent.png',intent)
        panel(folder/'INSPECTION.png',[source,proxy,intent],['Original GS / BUILD','Frozen reconstructed proxy','Old authored region4'],c['view']+' | No target edits yet',columns=3)
        grid=Image.open(folder/'source.png').convert('RGB');d=ImageDraw.Draw(grid)
        for x in range(0,c['width'],32):d.line((x,0,x,c['height']),fill=(190,190,190));d.text((x+1,2),str(x),fill='black')
        for y in range(32,c['height'],32):d.line((0,y,c['width'],y),fill=(190,190,190));d.text((1,y+1),str(y),fill='black')
        grid.save(folder/'AUTHORING_GRID.png')
        np.savez_compressed(folder/'FIRST_HIT.npz',face=face,regions=regions,depth=depth)
        records.append(dict(camera=c,source_cache=e['baseline'],source_cache_sha256=sha(e['baseline']),
                            target_pixels=int((h['regions']==4).sum()),files={f.name:sha(f) for f in folder.iterdir()}))
        print(c['view'],c['width'],c['height'],records[-1]['target_pixels'],flush=True)
    js(out/'INSPECTION.json',dict(started_utc=now(),records=records,asset=str(asset),mesh_sha256=sha(asset/'mesh.npz'),
        purpose='BUILD-only target definition inspection; all source/proxy frames precede selected-face freeze'))

if __name__=='__main__':main()

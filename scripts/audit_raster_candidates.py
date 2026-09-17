#!/usr/bin/env python3
"""Post-fit TRAIN diagnostics only; no method changes or geometric labels."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import cv2,numpy as np,torch
from scipy.spatial import cKDTree
from src import common,candidate_fusion as fusion,stroke_relations as draw
from run_raster_candidates import OUT,ARMS,git,sha,dump,paths_from,scaled,label,install_guard,as_segments


def main():
    if git('branch','--show-current')!='raster-state-candidates':raise RuntimeError('wrong branch')
    t=time.perf_counter();m=json.loads((OUT/'MANIFEST.json').read_text());dest=OUT/'lego';folder=dest/'diagnostics';folder.mkdir(exist_ok=True)
    access=install_guard(m,'lego',m['train_indices']);cams,_=common.load_cameras('lego');v=53;cam=scaled(cams[v],400)
    state=dict(np.load(dest/f'step1/state_{v:03d}.npz'));depth=torch.from_numpy(state['depth']);base=dict(np.load(dest/'baseline_initial.npz'))
    tree=cKDTree(base['p']);spacing=json.loads((dest/'step2.json').read_text())['spacing'];meta=json.loads((dest/'step4.json').read_text());sources={}
    for arm in ['B','C','D','N2']:
        L=dict(np.load(dest/f'step3/linelets_{arm}.npz'));dist=tree.query(L['p'])[0]/spacing;row=meta['arms'][arm]
        sources[arm]=dict(distance_to_A_in_spacing_quantiles=np.quantile(dist,[.1,.5,.9]).tolist(),fraction_within_one_spacing=float(np.mean(dist<=1)),
            new_prune_survival=row['new_after_prune']/row['new_linelets'],new_chain_survival=row['new_in_chains']/row['new_linelets'])
    # Surviving tags overlap: source counts are descriptive, NOT independent ablation.
    dc=json.loads((dest/'step3/clusters_D.json').read_text())['clusters'];pulled=np.load(dest/'step4/pulled_D.npz');good=pulled['good'][len(base['p']):]
    used=set(x-len(base['p']) for c in meta['arms']['D']['path_source_indices'] for x in c if x>=len(base['p']))
    tags={name:dict(initial=sum(i in c['source_tags'] for c in dc),after_prune=sum(i in c['source_tags'] and good[j] for j,c in enumerate(dc)),
                   in_chains=sum(i in dc[j]['source_tags'] for j in used)) for i,name in enumerate(m['fields']['arm_channels']['D'])}
    tags={k:{n:int(v) for n,v in d.items()} for k,d in tags.items()}
    # Extra visual control: same output linelet COUNT from already frozen matched
    # observation clusters. Deterministic random subset, never optimizes a picture.
    matched={};tiles=[]
    for arm in ['B','C','D']:
        cs={k:json.loads((dest/f'step3/matched_{arm}_{k}.json').read_text())['clusters'] for k in ['real','N2']};n=min(map(len,cs.values()));matched[arm]={}
        for kind,clusters in cs.items():
            selected=np.sort(np.random.default_rng(m['seed']).permutation(len(clusters))[:n]);matched[arm][kind]=selected.tolist()
            pp=as_segments(fusion.linelets([clusters[i] for i in selected]));projection=draw.project_paths(pp,cam,depth) if pp else []
            tiles.append(label(draw.draw_paths(projection,np.ones(len(pp),bool),(400,400)),f'{arm} {kind} | {n} linelets'))
    cv2.imwrite(str(folder/'count_matched_clusters_train053.png'),np.vstack([np.hstack(tiles[j:j+2]) for j in range(0,6,2)]))
    # Pre-marked-region audit: official RGB, raw A/D, final A/D. No GT overlays.
    channels=cv2.imread(str(dest/f'step1/channels_{v:03d}.png'));rgb=channels[26:426,:400]
    raw=cv2.imread(str(dest/f'step4/raw_{v:03d}.png'));images={'official':rgb,'raw A':raw[26:426,:400],'raw D':raw[452:852,:400]}
    full=[]
    for arm in ARMS:
        paths=paths_from(np.load(dest/f'step4/paths_{arm}.npz'));pp=draw.project_paths(draw.densify(paths),cam,depth) if paths else []
        im=draw.draw_paths(pp,np.ones(len(pp),bool),(400,400));full.append(label(im,f'{arm} final TRAIN53'))
        if arm in ['A','D']:images['final '+arm]=im
    cv2.imwrite(str(folder/'final_arms_train053.png'),np.vstack([np.hstack(full[:3]),np.hstack(full[3:])]))
    panels=[]
    for r in m['regions']:
        x0,y0,x1,y1=r['box'];row=[]
        for name,im in images.items():
            crop=im[y0:y1,x0:x1];scale=min(320/crop.shape[1],180/crop.shape[0]);crop=cv2.resize(crop,None,fx=scale,fy=scale,interpolation=cv2.INTER_NEAREST)
            canvas=np.full((180,320,3),255,np.uint8);canvas[:crop.shape[0],:crop.shape[1]]=crop;row.append(label(canvas,r['id']+' '+name))
        panels.append(np.hstack(row))
    cv2.imwrite(str(folder/'preregistered_regions.png'),np.vstack(panels))
    dump(folder/'audit.json',dict(commit=git('rev-parse','HEAD'),script_sha256=sha(__file__),sources=sources,D_overlapping_source_survival=tags,
         count_matched_cluster_ids=matched,seconds=time.perf_counter()-t,regions_used_for_method=False))
    dump(folder/'access.json',access)


if __name__=='__main__':main()

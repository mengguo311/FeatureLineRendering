#!/usr/bin/env python3
"""Independent G1 provenance, layer, band, control, decode and rerun audits."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
import cv2
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.verify_adaptive_mass_probe import sha


def camera_semantics(source,camera):
    return np.array_equal(source['camera_K'],camera['native_K']) and np.array_equal(source['w2c'],camera['w2c']) and source['native_alpha'].shape==(camera['native_height'],camera['native_width'])


def layout_semantics(run):
    record=json.loads((run/'diagnostics/LAYOUT.json').read_text())
    return record['science_unchanged'] and all(sha(run/p)==h for p,h in record['science_sha256'].items()) and all(sha(run/'diagnostics'/p)==h for p,h in record['png_sha256'].items())


def layer_semantics(data):
    off=data['events.offsets'];z=data['events.z'];w=data['events.w'].astype('f8');sizes=np.diff(off);pix=np.repeat(np.arange(len(sizes)),sizes)
    assignment=data['layers.assignment'];mass=data['layers.layer_mass'];depth=data['layers.layer_depth'];loff=data['layers.layer_offsets'];scale=data['layers.local_scale']
    start=np.zeros(len(z),bool);start[off[:-1][sizes>0]]=True
    if len(z)>1:start[1:] |= np.diff(z)>3*scale.ravel()[pix[1:]]
    expected=np.cumsum(start)-1
    checks=dict(assignment=np.array_equal(assignment,expected),layer_offsets=np.array_equal(loff,np.r_[0,np.cumsum(np.bincount(pix[start],minlength=len(sizes)))]))
    if assignment.shape!=z.shape or np.any(assignment<0) or np.any(assignment>=len(mass)):return dict(passed=False,checks=checks)
    actual=np.bincount(assignment,weights=w,minlength=len(mass))
    actual_z=np.bincount(assignment,weights=w*z,minlength=len(mass))/np.maximum(actual,1e-12)
    close=lambda a,b:bool(np.allclose(a,b,rtol=0,atol=1e-10))
    checks.update(layer_mass=close(actual,mass),layer_depth=close(actual_z,depth),histogram=close(data['layers.histogram_p'],w/np.maximum(mass[assignment],1e-12)))
    A=np.bincount(pix,weights=w,minlength=len(sizes)).reshape(scale.shape)
    checks['retained_and_overflow']=close(data['layers.retained_mass'].sum(-1)+data['layers.overflow_mass'],A)
    checks['four_layers']=data['layers.retained_mass'].shape==(*scale.shape,4)
    return dict(passed=all(checks.values()),checks=checks)


def band_semantics(response,field,normalization):
    positive=response[response>0]
    thresholds=np.array([np.percentile(positive,[hi,lo]) if len(positive) else [0.,0.] for hi,lo in [(95,70),(90,60)]])
    checks=dict(response=np.array_equal(response,field['response']),normalized=np.array_equal(response/max(normalization,1e-12),field['normalized_soft']),thresholds=np.array_equal(thresholds,field['thresholds']))
    for i,grid in enumerate(['95_70','90_60']):
        band=field['band_'+grid];center=field['center_'+grid];anchors=field['anchors_'+grid];nms=field['nms_'+grid]
        hi,lo=thresholds[i]
        checks[grid+'_positive']=bool(np.all(~band|((response>0)&(response>=lo))))
        checks[grid+'_anchors']=np.array_equal(anchors,nms&(response>0)&(response>=hi))
        checks[grid+'_inclusion']=bool(np.all(~anchors|center) and np.all(~center|band))
    checks['nested']=bool(np.all(~field['band_95_70']|field['band_90_60']))
    return dict(passed=all(checks.values()),checks=checks)


def load_arrays(path,ledger,root):
    with np.load(path,allow_pickle=False) as f:data={k:f[k] for k in f.files}
    ledger[str(path.relative_to(root))]={k:dict(shape=list(v.shape),dtype=str(v.dtype),sha256=hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest()) for k,v in data.items()}
    if not all(np.isfinite(v).all() for v in data.values()):raise ValueError('nonfinite arrays '+str(path))
    return data


def main():
    import argparse
    from src.corrected_audit import audit_policy,bootstrap_reads_before_policy,verified_source_exception
    from src.adaptive_layers import local_depth_scale
    from src.adaptive_evidence import prefix_control,transform_control
    from scripts.render_adaptive_g1 import CONTROLS,CHANNELS,ink_metrics,matched_mask
    from scripts.verify_adaptive_mass_probe import verify_npz
    from scripts.render_topk_layered_probe import frozen_inputs
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT/'out/adaptive_mass_layered_probe')
    args=parser.parse_args();root=args.root.resolve();art=ROOT/'artifacts/adaptive_mass_layered_probe'
    cfg=frozen_inputs(art)
    records=[(s,v) for s in ['lego','chair','drums','ficus'] for v in [1,27,53,79]]
    expected={'GATES.json','NORMALIZATION.json'}|{f'native/{s}_{v}.{ext}' for s,v in records for ext in ['json','npz']}|{f'{folder}/{s}_{v}_{c}.{ext}' for s,v in records for c in CONTROLS for folder in ['raw','final'] for ext in ['npz','json']}|{f'figures/{s}_RGB.png' for s,v in records}|{f'figures/{s}_{ch}_group{g}.png' for s,v in records for ch in CHANNELS for g in range(3)}
    expected |= {'diagnostics/LAYOUT.json'}|{f'diagnostics/{s}_mechanisms_{g}.png' for s,v in records for g in range(4)}
    bootstrap=json.loads((art/'BOOTSTRAP_READS.json').read_text());exceptions=bootstrap['directories']+[verified_source_exception(p,h) for p,h in bootstrap['sources'].items()]
    checks={};arrays={};hashes={};audits={};decoded=0;native_checks={};stage_results={};scale_cache={}
    for run in ['g1_run','g1_rerun']:
        output=root/run;ledger={};arrays[run]=ledger
        inventory={str(p.relative_to(output)):p for p in output.rglob('*') if p.is_file() and p.suffix in ['.json','.npz','.png'] and p.name!='allowlist.json'}
        checks[run+':inventory']=set(inventory)==expected;hashes[run]={k:sha(p) for k,p in inventory.items()}
        policy=json.loads((output/'allowlist.json').read_text());trace=(root/'setup'/(run+'.strace')).read_text()
        audit=audit_policy(trace,policy,output,policy['bootstrap_files']+exceptions)
        audit['bootstrap_before_policy']=bootstrap_reads_before_policy(trace,output/'allowlist.json',policy['bootstrap_files']+exceptions)
        audit['source_unchanged']=all(sha(p)==h for key in ['source_hashes','upstream_source_hashes'] for p,h in policy[key].items())
        audit['passed'] &= audit['bootstrap_before_policy'] and audit['source_unchanged'];audits[run]=audit
        layout_policy=json.loads((output/'diagnostics/allowlist.json').read_text());layout_trace=(root/'setup'/(run+'_layout.strace')).read_text()
        layout_audit=audit_policy(layout_trace,layout_policy,output/'diagnostics',exceptions+layout_policy['bootstrap_files'])
        layout_audit['bootstrap_before_policy']=bootstrap_reads_before_policy(layout_trace,output/'diagnostics/allowlist.json',exceptions+layout_policy['bootstrap_files'])
        layout_audit['source_unchanged']=all(sha(p)==h for p,h in layout_policy['source_hashes'].items())
        layout_audit['passed'] &= layout_audit['source_unchanged'] and layout_audit['bootstrap_before_policy'];audits[run+'_layout']=layout_audit
        checks[run+':layout_preservation']=layout_semantics(output)
        normalization=json.loads((output/'NORMALIZATION.json').read_text());positive={ch:[] for ch in CHANNELS}
        for scene,view in records:
            source_path=output/'native'/f'{scene}_{view}.npz';source=load_arrays(source_path,ledger,output)
            native=verify_npz(source_path,.95,128);native_checks[f'{run}:{scene}:{view}']=native['passed']
            checks[f'{run}:{scene}:{view}:frozen_camera']=camera_semantics(source,cfg['scenes'][scene]['cameras'][str(view)])
            keys=['offsets','ids','stream_position','z','alpha','T','w','rgb','tail_rgb','tail_alpha','final_T','native_final_T','count']
            master={k:source[k] for k in keys};fixed={k:source['fixed16.'+k] for k in keys};alpha=source['native_alpha']
            primary=prefix_control(master,alpha,.9,128);reference={};rawfull=None
            for control in CONTROLS:
                stem=f'{scene}_{view}_{control}';raw=load_arrays(output/'raw'/(stem+'.npz'),ledger,output);final=load_arrays(output/'final'/(stem+'.npz'),ledger,output)
                metrics=json.loads((output/'final'/(stem+'.json')).read_text());row={}
                e=primary
                if control in ['uniform','shuffled_ids','shuffled_depths']:e=transform_control(primary,control,20260921+view+(1000 if control=='shuffled_depths' else 0))
                elif control.startswith('k'):e=prefix_control(fixed,alpha,None,int(control[1:]))
                elif control.startswith('tau'):
                    t,k=control[3:].split('_');e=prefix_control(master,alpha,int(t)/100,int(k))
                row['event_provenance']=all(np.array_equal(raw['events.'+k],e[k]) for k in ['offsets','ids','z','w','stream_position'])
                layer=layer_semantics(raw);row['layers']=layer['passed']
                off=e['offsets'];sizes=np.diff(off);pix=np.repeat(np.arange(len(sizes)),sizes);front=np.zeros(len(sizes));front[sizes>0]=e['z'][off[:-1][sizes>0]]
                scale_key=hashlib.sha256(front.tobytes()).hexdigest()
                if scale_key not in scale_cache:scale_cache[scale_key]=hashlib.sha256(local_depth_scale(front.reshape(alpha.shape)).tobytes()).hexdigest()
                row['local_scale']=hashlib.sha256(raw['layers.local_scale'].tobytes()).hexdigest()==scale_cache[scale_key]
                assignment=raw['layers.assignment'];n=len(raw['layers.layer_mass'])
                rgb=np.stack([np.bincount(assignment,weights=e['w'].astype('f8')*e['rgb'][:,c],minlength=n) for c in range(3)],axis=-1)
                row['layer_rgb']=bool(np.allclose(rgb,raw['layers.layer_rgb'],rtol=0,atol=1e-10))
                row['tail_residual']=np.array_equal(raw['layers.tail_alpha'],e['tail_alpha']) and np.array_equal(raw['layers.tail_rgb'],e['tail_rgb'])
                lcounts=np.diff(raw['layers.layer_offsets']);expected_index=raw['layers.layer_offsets'][:-1,None]+np.arange(4)[None,:];expected_index=np.where(np.arange(4)[None,:]<lcounts[:,None],expected_index,-1).reshape(*alpha.shape,4)
                row['earliest_four']=np.array_equal(raw['layers.retained_index'],expected_index)
                if control=='full':rawfull={ch:raw[ch+'.response'].copy() for ch in CHANNELS}
                for ch in CHANNELS:
                    f={k[len(ch)+1:]:v for k,v in final.items() if k.startswith(ch+'.')};response=raw[ch+'.response']
                    row[ch+':bands']=band_semantics(response,f,normalization[ch])['passed']
                    if control=='full':
                        positive[ch].append(response[response>0]);reference[ch]={k:f[k].copy() for k in ['response','band_95_70']}
                    ref=reference[ch];count=min(int(ref['band_95_70'].sum()),int(f['band_95_70'].sum()))
                    row[ch+':matched']=np.array_equal(f['matched_full'],matched_mask(ref['response'],ref['band_95_70'],count)) and np.array_equal(f['matched_control'],matched_mask(response,f['band_95_70'],count))
                    row[ch+':metrics']=all(ink_metrics(f['band_'+g])==metrics[ch][g] for g in ['95_70','90_60'])
                    if control=='no_ids':row[ch+':ID_factor_bound']=bool(np.all(rawfull[ch]<=response+2e-6))
                stage_results[run+':'+stem]=row
                print('G1 verified',run,stem,all(row.values()),flush=True)
                del raw,final,e;gc_collect()
            del source,master,fixed,primary
        checks[run+':normalization']=all(normalization[ch]==(float(np.percentile(np.concatenate(positive[ch]),99)) if any(len(r) for r in positive[ch]) else 1.) for ch in CHANNELS)
        for name,path in inventory.items():
            if path.suffix=='.png':
                im=cv2.imread(str(path));checks[run+':'+name+':decode']=im is not None;decoded+=int(im is not None)
        del positive
    checks.update(byte_rerun=hashes['g1_run']==hashes['g1_rerun'],array_rerun=arrays['g1_run']==arrays['g1_rerun'],native_semantics=all(native_checks.values()),access=all(r['passed'] for r in audits.values()),all_control_semantics=all(all(r.values()) for r in stage_results.values()))
    result=dict(passed=all(checks.values()),checks=checks,hashes=hashes,arrays=arrays,native=native_checks,controls=stage_results,decoded_pngs=decoded,audits=audits,video='NOT_APPLICABLE: no G2/G3 video stage reached')
    (art/'G1_VERIFICATION.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(passed=result['passed'],checks={k:v for k,v in checks.items() if ':decode' not in k},decoded_pngs=decoded),indent=2))
    sys.exit(0 if result['passed'] else 1)


def gc_collect():
    import gc
    gc.collect()


if __name__=='__main__':main()

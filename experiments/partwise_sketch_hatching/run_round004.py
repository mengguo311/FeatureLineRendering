"""One frozen post-hoc stage-attribution diagnostic, CPU only."""
import stage_attribution as sa
import argparse, collections, datetime, hashlib, json, shutil, subprocess, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

W=Path(__file__).resolve().parents[2]
R=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_004')
P=R.parent/'round_003'; P2=R.parent/'round_002'
D=W/'docs/partwise_sketch_hatching/round_004'
CFG=json.loads((W/'docs/partwise_sketch_hatching/round_001/PROTOCOL.json').read_text())
START=time.monotonic()


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def write(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix('.tmp')
    t.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False,
                           default=lambda v:v.item() if isinstance(v,np.generic) else str(v))+'\n');t.replace(p)


def status(stage,**kw):
    obj=json.loads((R/'STATUS.json').read_text())
    obj.update(stage=stage,updated_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**kw)
    write(R/'STATUS.json',obj)


def resources():
    root=shutil.disk_usage('/').free;hdd=shutil.disk_usage('/mnt/hdd1').free
    used=sum(p.stat().st_size for p in R.parent.parent.rglob('*') if p.is_file())
    deps=sum(p.stat().st_size for p in (W/'.runtime_p0').rglob('*') if p.is_file())
    assert root>=2**30 and hdd>=10*2**30 and used+deps<12*2**30
    assert time.monotonic()-START<570
    assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat('2026-10-21T05:24:18.844098+09:00')
    assert sorted(sa.ta.os.sched_getaffinity(0))==[0,1]
    return {'root_free_bytes':root,'hdd_free_bytes':hdd,'task_bytes':used,'dependency_bytes':deps,
            'cpu_affinity':[0,1],'threads_max':2,'GPU':False}


def verify_prior():
    seal=json.loads((P/'SEAL.json').read_text());m=json.loads((P/'SHA256_MANIFEST.json').read_text())
    assert sha(P/'SHA256_MANIFEST.json')==seal['manifest_sha256']
    for f in m['files']:
        p=(W if f['root']=='worktree' else P)/f['path']
        assert sha(p)==f['sha256'] and p.stat().st_size==f['bytes'],str(p)
    return {'verified_files':len(m['files']),'seal_sha256':sha(P/'SEAL.json')}


def prepare():
    assert not (D/'ASSET_LOCK.json').exists(); resources()
    verified=verify_prior();write(R/'PRIOR_SEAL_VERIFY.json',verified)
    missing=json.loads((P/'MISSING_SUPPORT_SAMPLES.json').read_text())['records']
    s=dict(np.load(P/'samples.npz'));pairs=[];raw={}
    assert len(missing)==61
    for n,rec in enumerate(missing):
        kind,i,j=rec['trajectory'],rec['frame'],rec['sample_global_index']
        if (kind,i) not in raw:raw[kind,i]=dict(np.load(P/'raw'/kind/f'{i:04d}.npz'))
        z=raw[kind,i];owner=int(s['owner'][j]);assert str(s['stroke_ids'][owner])==rec['stroke_id']
        assert z['eligible_geometry'][j] and not z['ambiguity'][j] and z['distance'][0,j]>1.5
        candidates=np.flatnonzero((s['owner']==owner)&z['eligible_geometry']&~z['ambiguity']&(z['distance'][0]<=1.5))
        control=int(candidates[np.lexsort((candidates,abs(candidates-j)))[0]]) if len(candidates) else None
        pairs.append({'pair_index':n,'trajectory':kind,'frame':i,'owner':owner,'stroke_id':rec['stroke_id'],
                      'case_index':j,'control_index':control})
    sel={'rule':json.loads((D/'PROTOCOL.json').read_text())['selection'],
         'case_count':len(pairs),'frame_count':len(raw),'pairs':pairs,
         'unique_control_count':len({(p['trajectory'],p['frame'],p['control_index']) for p in pairs if p['control_index'] is not None}),
         'missing_control_count':sum(p['control_index'] is None for p in pairs)}
    assert len(raw)==14;write(R/'SELECTION.json',sel)
    sources=[W/'experiments/partwise_sketch_hatching'/n for n in
             ['core.py','temporal_audit.py','stage_attribution.py','test_stage_attribution.py','test_temporal_audit.py','run_round004.py','round004_receipt.py']]
    sources += [D/'PROTOCOL.json',D/'REVIEW_LIMITS_ZH.md',W/'docs/partwise_sketch_hatching/round_001/PROTOCOL.json',
                W/'docs/partwise_sketch_hatching/round_003/PROTOCOL.json',W/'docs/partwise_sketch_hatching/round_003/ASSET_LOCK.json',
                W/'docs/partwise_sketch_hatching/experiment_outline_v1.md']
    assets=[P/'SEAL.json',P/'SHA256_MANIFEST.json',P/'NEXT.json',P/'MISSING_SUPPORT_SAMPLES.json',P/'samples.npz',P/'metrics.json',
            P2/'assets/lamp_mesh.npz',P2/'strokes/mixed.npz',P2/'camera_trajectories.json',R/'SELECTION.json']
    for kind,i in sorted(raw):assets.extend([P/'raw'/kind/f'{i:04d}.npz',P/'frames'/kind/f'{i:04d}.png'])
    lock={'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip(),
          'protocol_commit':'5917d908','sources':{str(p.relative_to(W)):sha(p) for p in sources},
          'inputs':{str(p):sha(p) for p in assets},'prior_seal':verified,'resources':resources(),
          'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write(D/'ASSET_LOCK.json',lock)
    status('selection_and_hash_lock_prepared',artifacts=['SELECTION.json','PRIOR_SEAL_VERIFY.json'])
    print(json.dumps({k:sel[k] for k in ['case_count','frame_count','unique_control_count','missing_control_count']}))


def verify_lock():
    assert subprocess.check_output(['git','branch','--show-current'],cwd=W,text=True).strip()=='partwise-sketch-hatching-p0p1-v01'
    lock=json.loads((D/'ASSET_LOCK.json').read_text())
    for p,h in lock['sources'].items():assert sha(W/p)==h,p
    for p,h in lock['inputs'].items():assert sha(p)==h,p
    rel=str((D/'ASSET_LOCK.json').relative_to(W))
    subprocess.run(['git','ls-files','--error-unmatch',rel],cwd=W,capture_output=True,check=True)
    assert not subprocess.check_output(['git','diff','HEAD','--',rel],cwd=W)
    return lock


def save_owner(path,d):
    arrays={'trace_'+k:v for k,v in d['trace'].items()}
    arrays.update({'stage_'+k:v for k,v in d['stages'].items()})
    arrays.update({k:v for k,v in d.items() if k not in ['trace','stages']})
    np.savez_compressed(path,**arrays)


def load_owner(path):
    z=dict(np.load(path));d={'trace':{},'stages':{}}
    for k,v in z.items():
        if k.startswith('trace_'):d['trace'][k[6:]]=v
        elif k.startswith('stage_'):d['stages'][k[6:]]=v
        else:d[k]=v
    return d


def panels(kind,i,render,pairs,samples,z):
    im=Image.fromarray(render['full']).convert('RGB');draw=ImageDraw.Draw(im)
    for p in pairs:
        for key,color in [('case_index','red'),('control_index','blue')]:
            if p[key] is None:continue
            x,y=z['uv'][p[key]];draw.ellipse((x-2,y-2,x+2,y+2),outline=color)
    fullpath=R/'figures'/f'{kind}_{i:04d}_full.png';im.save(fullpath)
    owner_panels=[]
    for owner in sorted(render['selected']):
        d=render['selected'][owner]
        indices=sorted({p[k] for p in pairs if p['owner']==owner for k in ['case_index','control_index'] if p[k] is not None})
        uv=z['uv'][indices];lo=np.maximum(0,np.floor(uv.min(axis=0)).astype(int)-8);hi=np.minimum(512,np.ceil(uv.max(axis=0)).astype(int)+9)
        # Identical crop on six actual stages; full object is supplied separately.
        views=[('Before z-test',ta_down(d['pre_z'])),('After z-test',ta_down(d['stages']['raw'])),
               ('Width + AA',d['stages']['downsample']),('ID support',d['identified'].astype(np.uint8)*255),
               ('Hatch influence',d['hatch_leave_one_out_delta'].astype(np.uint8)),('Final influence',d['full_leave_one_out_delta'].astype(np.uint8))]
        panel=Image.new('RGB',(6*190,240),'white');pd=ImageDraw.Draw(panel)
        for k,(title,a) in enumerate(views):
            crop=Image.fromarray(255-a).convert('RGB').crop((*lo,*hi));crop.thumbnail((180,170))
            panel.paste(crop,(k*190+(190-crop.width)//2,55+(170-crop.height)//2))
            pd.text((k*190+4,32),title,fill='black')
        pd.text((4,5),f'{kind} {i:02d} | {samples["stroke_ids"][owner]} | all case/control neighborhood',fill='black')
        op=R/'figures'/f'{kind}_{i:04d}_owner{owner}.png';panel.save(op);owner_panels.append(op)
    return fullpath,owner_panels


def ta_down(a):return sa.ta.downsample(a,2)


def contact(entries,path,cols=4,tile=256):
    sheet=Image.new('RGB',(cols*tile,((len(entries)+cols-1)//cols)*(tile+28)),'white');draw=ImageDraw.Draw(sheet)
    for n,(title,p) in enumerate(entries):
        x=n%cols*tile;y=n//cols*(tile+28)
        with Image.open(p) as im:sheet.paste(im.convert('RGB').resize((tile,tile)),(x,y+28))
        draw.text((x+3,y+5),title,fill='black')
    sheet.save(path)


def evaluate():
    verify_lock();resources();assert not (R/'ATTRIBUTION.json').exists()
    selection=json.loads((R/'SELECTION.json').read_text());samples=dict(np.load(P/'samples.npz'))
    meshz=np.load(P2/'assets/lamp_mesh.npz');mesh=sa.ta.core.finalize_mesh(meshz['vertices'],meshz['faces'],meshz['parts'])
    strokes=sa.ta.load_strokes(P2/'strokes/mixed.npz');cams=json.loads((P2/'camera_trajectories.json').read_text())
    grouped=collections.defaultdict(list)
    for p in selection['pairs']:grouped[p['trajectory'],p['frame']].append(p)
    (R/'figures').mkdir(exist_ok=True);records=[];frames=[];allpanels=[];ownerpanels=[]
    for (kind,i),pairs in sorted(grouped.items()):
        resources();t=time.monotonic();folder=R/'raw'/kind/f'{i:04d}';folder.mkdir(parents=True,exist_ok=True)
        params=cams[kind][i];assert params['index']==i and params['stroke_digest']==sa.ta.core.stroke_digest(strokes)
        owners={p['owner'] for p in pairs};render=sa.replay_frame(mesh,strokes,CFG,params,owners)
        z=dict(np.load(P/'raw'/kind/f'{i:04d}.npz'))
        np.testing.assert_array_equal(render['full'],np.asarray(Image.open(P/'frames'/kind/f'{i:04d}.png')))
        np.testing.assert_array_equal(render['hatch'],z['hatch']);np.testing.assert_array_equal(render['count'],z['overlap_count'])
        np.savez_compressed(folder/'common.npz',depth=render['depth'],parts=render['parts'],hatch=render['hatch'],count=render['count'],
                            full=render['full'],structure=render['structure'])
        for owner,d in render['selected'].items():save_owner(folder/f'owner_{owner}.npz',d)
        unique=sorted({p[k] for p in pairs for k in ['case_index','control_index'] if p[k] is not None})
        sc={k:samples[k][unique] for k in ['xyz','parts']}
        c=sa.ta.core.camera(params['azimuth_deg'],params['elevation_deg'],params['distance'],512,600)
        expected=sa.ta.expected_samples(sc,CFG['asset'],c)
        np.testing.assert_allclose(expected['uv'],z['uv'][unique],atol=1e-12,rtol=0)
        np.testing.assert_array_equal(expected['eligible_geometry'],z['eligible_geometry'][unique])
        cache={}
        for n,j in enumerate(unique):
            owner=int(samples['owner'][j]);d=render['selected'][owner]
            a=sa.record_stages(z['uv'][j],expected['eligible_geometry'][n],d,int(samples['parts'][j]))
            dist=a['stages']['identified']['nearest_px'];original=float(z['distance'][0,j])
            assert dist is not None and abs(dist-original)<1e-10
            assert not sa.ta.ambiguous_samples(z['uv'][j:j+1],render['count'])[0]
            assert a['stages']['combined_hatch']['supported']==a['stages']['identified']['supported']
            a.update(sample_global_index=j,stroke_id=str(samples['stroke_ids'][owner]),owner=owner,
                     world_xyz=samples['xyz'][j].tolist(),uv=z['uv'][j].tolist(),weight_world=float(samples['weight'][j]),
                     original_support_distance_px=original,original_ambiguity=bool(z['ambiguity'][j]),
                     analytic_depth=float(expected['expected_depth'][n]),sample_depth=float(expected['sample_depth'][n]),
                     raw_path=str((folder/f'owner_{owner}.npz').relative_to(R)))
            cache[j]=a
        for p in pairs:
            records.append({'pair':p,'case':cache[p['case_index']],
                            'control':cache[p['control_index']] if p['control_index'] is not None else None})
        full,ops=panels(kind,i,render,pairs,samples,z);allpanels.append((f'{kind} {i:02d} | red: case; blue: control',full));ownerpanels+=ops
        f={'trajectory':kind,'frame':i,'cases':len(pairs),'owners':sorted(owners),'unique_samples':len(unique),
           'full_matches':True,'hatch_matches':True,'count_matches':True,'seconds':time.monotonic()-t}
        frames.append(f);write(R/'PARTIAL_ATTRIBUTION.json',{'frames':frames,'records':records})
        status(f'traced_{len(frames)}_of_14_frames',artifacts=['SELECTION.json','PARTIAL_ATTRIBUTION.json','raw/','figures/'])
        print(json.dumps(f),flush=True)
    assert len(records)==61 and len(frames)==14
    assert {x['pair']['pair_index'] for x in records}==set(range(61))
    contact(allpanels,R/'figures/full_view_contact_sheet.png',cols=4,tile=320)
    for n in range(0,len(ownerpanels),8):
        page=ownerpanels[n:n+8];im=Image.new('RGB',(1140,len(page)*240),'white')
        for j,p in enumerate(page):
            with Image.open(p) as a:im.paste(a,(0,j*240))
        im.save(R/'figures'/f'stage_contact_sheet_{n//8:02d}.png')
    write(R/'ATTRIBUTION.json',{'complete':True,'frames':frames,'records':sorted(records,key=lambda x:x['pair']['pair_index']),
                              'resources':resources(),'stage_order':sa.STAGE_NAMES,
                              'scope':'Observed support-loss stages, no renderer repair; final influence is separate.'})
    summarize()


def summarize():
    data=json.loads((R/'ATTRIBUTION.json').read_text());sel=json.loads((R/'SELECTION.json').read_text())
    result={}
    for group in ['case','control']:
        rows=[x[group] for x in data['records'] if x[group] is not None]
        counts=collections.Counter(x['loss_stage'] for x in rows)
        result[group]={'paired_count':len(rows),'loss_stage_counts':dict(counts),
                       'local_final_nonzero_influence_count':sum(x['final_influence']['full']['nonzero']['supported'] for x in rows),
                       'local_final_above_0_04_influence_count':sum(x['final_influence']['full']['above_0_04']['supported'] for x in rows),
                       'local_hatch_nonzero_influence_count':sum(x['final_influence']['hatch']['nonzero']['supported'] for x in rows),
                       'stage_support_counts':{k:sum(x['stages'][k]['supported'] for x in rows) for k in sa.STAGE_NAMES},
                       'per_id':{sid:dict(collections.Counter(x['loss_stage'] for x in rows if x['stroke_id']==sid)) for sid in sorted({x['stroke_id'] for x in rows})}}
    green=json.loads((R/'TESTS_GREEN_FINAL.json').read_text());reg=json.loads((R/'INHERITED_TESTS.json').read_text())
    gates={'all_61_cases':len(data['records'])==61,'all_14_frames_exact_replay':len(data['frames'])==14 and all(f['full_matches'] and f['hatch_matches'] and f['count_matches'] for f in data['frames']),
           'all_controls_exist':sel['missing_control_count']==0,'all_controls_supported':result['control']['loss_stage_counts']=={'supported':61},
           'all_cases_missing':result['case']['stage_support_counts']['identified']==0,'toy_green':green['returncode']==0,'inherited_green':reg['returncode']==0}
    inherited=json.loads((P/'metrics.json').read_text())
    write(R/'metrics.json',{'evaluation_complete':True,'diagnostic_go':all(gates.values()),'gates':gates,
                           'groups':result,'unique_control_count':sel['unique_control_count'],'frame_count':14,
                           'input_samples_per_frame':54687,'prior_eligible_fraction_of_visible':{k:v['eligible_fraction_of_visible'] for k,v in inherited['trajectories'].items()},
                           'statistical_scope':'61 selected failures; paired controls may repeat; no new population metric',
                           'mean_trace_seconds_per_affected_frame':float(np.mean([f['seconds'] for f in data['frames']])),
                           'resources':resources()})
    status('evaluated_pending_independent_data_validation',scientific_verdict='STAGE_DIAGNOSTIC_GO' if all(gates.values()) else 'STAGE_DIAGNOSTIC_NO_GO',tests={'gates':gates},artifacts=['ATTRIBUTION.json','metrics.json','raw/','figures/'])
    print(json.dumps({'gates':gates,'groups':result,'unique_controls':sel['unique_control_count']},indent=2),flush=True)


def validate():
    verify_lock();resources();assert not (R/'VALIDATION.json').exists()
    data=json.loads((R/'ATTRIBUTION.json').read_text());sel=json.loads((R/'SELECTION.json').read_text())
    missing=json.loads((P/'MISSING_SUPPORT_SAMPLES.json').read_text())['records'];cache={};count=0
    expected={(x['trajectory'],x['frame'],x['sample_global_index']) for x in missing}
    actual={(x['pair']['trajectory'],x['pair']['frame'],x['case']['sample_global_index']) for x in data['records']}
    assert actual==expected and len(actual)==61
    for pair in data['records']:
        for group in ['case','control']:
            row=pair[group]
            if row is None:continue
            rp=row['raw_path']
            if rp not in cache:
                d=load_owner(R/rp);common=np.load((R/rp).parent/'common.npz');cache[rp]=(d,dict(common))
            d,common=cache[rp]
            recomputed=sa.record_stages(np.array(row['uv']),True,d,1)
            for k in ['stages','extra_stages','flags','loss_stage','witnesses','final_influence']:assert recomputed[k]==row[k],(group,k)
            np.testing.assert_array_equal(d['stages']['downsample'],sa.ta.downsample(d['stages']['clipped']))
            np.testing.assert_array_equal(d['omitted_hatch'],sa.ta.downsample(d['omitted_clipped']))
            np.testing.assert_array_equal(d['omitted_full'],sa.full_image(d['omitted_clipped'],common['structure']))
            np.testing.assert_array_equal(d['hatch_leave_one_out_delta'],abs(common['hatch'].astype(np.int16)-d['omitted_hatch'].astype(np.int16)))
            np.testing.assert_array_equal(d['full_leave_one_out_delta'],abs(common['full'].astype(np.int16)-d['omitted_full'].astype(np.int16)))
            count+=1
    prior=verify_prior()
    result={'complete':True,'paired_rows_recomputed':count,'unique_owner_frame_archives':len(cache),
            'all_case_keys_exact':True,'all_saved_stage_metrics_exact':True,'all_omitted_composites_exact':True,
            'prior_seal':prior,'resources':resources()}
    write(R/'VALIDATION.json',result);status('validated_pending_report',tests={'validation':result})
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','evaluate','validate']);a=p.parse_args()
    try:globals()[a.action]()
    except Exception as exc:
        status('execution_failure',execution_state='engineering_invalid',scientific_verdict='INCOMPLETE',error=f'{type(exc).__name__}: {exc}')
        raise

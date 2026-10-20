"""One immutable rendered planar axial_zoom sequence; CPU only, serial."""
import round016_common as c
import argparse,copy,hashlib,importlib.metadata,json,subprocess,sys,time
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import planar_fragments_exact as candidate
import physical_area_reference as oracle
import mesh_attachment as adapter
import round010_fixture as fixture
import planar_temporal_metrics as metrics
import run_round015 as old
from planar_axial_reference import project_prescribed
P=json.loads((c.D/'PROTOCOL.json').read_text())
NAMES=['ribbon','owned','occluded','visible','unsupported']
NEW=['round016_common.py','round016_receipt.py','build_round016_protocol.py','planar_axial_reference.py','test_planar_axial_reference.py','run_round016.py','seal_round016.py','run_round016_tests.py']

def prepare():
    assert not (c.D/'ASSET_LOCK.json').exists()
    prior=json.loads((c.W/'docs/partwise_sketch_hatching/round_015/ASSET_LOCK.json').read_text())
    for name,h in prior['sources'].items():assert c.sha(c.W/name)==h,name
    paths={c.W/p for p in prior['sources']}|{c.W/'experiments/partwise_sketch_hatching'/p for p in NEW}|{c.D/'PROTOCOL.json'}
    paths|={p for p in (c.W/'docs/partwise_sketch_hatching/round_015').iterdir() if p.is_file()}
    inputs=[p for p in c.P.rglob('*') if p.is_file() and 'runtime' not in p.relative_to(c.P).parts]
    c.write(c.D/'ASSET_LOCK.json',{'protocol_commit':'083da186','implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.W,text=True).strip(),'sources':{str(p.relative_to(c.W)):c.sha(p) for p in sorted(paths)},'inputs':{str(p):c.sha(p) for p in sorted(inputs)},'prior_seal':c.verify_prior(),'resources':c.resources(),'dependencies':{n:importlib.metadata.version(n) for n in ['numpy','scipy','Pillow']}})
    c.status('locked_awaiting_evaluation')

def geometry():
    mesh,cam,path,owners,segments,_,_=fixture.fixture(P,P['case'])
    return mesh,cam,path,owners,segments

def analytic(frame):
    eye=np.asarray(frame['eye']);spec=P['case'];g=P['geometry']
    assert np.array_equal(frame['R'],np.eye(3)) and np.array_equal(eye[:2],[0.,0.])
    owner_z=g['analytic_owner']['z'];foreground_z=spec['extra']['z']
    path=project_prescribed(spec['projected_path'],owner_z,eye[2])
    bounds=project_prescribed(np.asarray(g['analytic_owner']['bounds_high_xyxy']).reshape(2,2),owner_z,eye[2]).ravel().tolist()
    extra=copy.deepcopy(spec['extra'])
    extra['bounds_high_xyxy']=project_prescribed(np.asarray(extra['bounds_high_xyxy']).reshape(2,2),foreground_z,eye[2]).ravel().tolist()
    extra['z']=foreground_z-eye[2]
    # Whole ribbon is owned; foreground vertical strip covers both transverse edges.
    # Verify sufficient conditions before applying the independent closed-form check.
    lo=np.minimum(path[0],path[-1])-1.;hi=np.maximum(path[0],path[-1])+1.
    assert np.all(lo>np.array(bounds[:2])) and np.all(hi<np.array(bounds[2:]))
    q=extra['bounds_high_xyxy'];d=path[-1]-path[0];length=np.linalg.norm(d)
    ys=path[0,1]+(np.asarray([q[0],q[2]])-path[0,0])*d[1]/d[0]
    assert min(ys)-length/abs(d[0])>q[1] and max(ys)+length/abs(d[0])<q[3]
    assert q[0]>min(path[:,0])+1. and q[2]<max(path[:,0])-1.
    clean,raw,glob=oracle.reference(path,128,2.,bounds,owner_z-eye[2],extra)
    high=clean['visible']*.8;quantized=np.uint8(np.clip(high,0,1)*255)
    final=np.asarray(Image.fromarray(quantized).resize((64,64),Image.Resampling.LANCZOS))
    return path,bounds,extra,clean,raw,glob,high,quantized,final

def correspondence(path,bounds,extra):
    cfg=P['correspondence'];t=(np.arange(cfg['samples'])+.5)/cfg['samples']
    points=path[0]+t[:,None]*(path[-1]-path[0]);uv=(points+.5)/2-.5
    x,y=points.T;b=np.asarray(bounds);q=np.asarray(extra['bounds_high_xyxy'])
    owner=(x>=b[0])&(x<=b[2])&(y>=b[1])&(y<=b[3])
    hidden=(x>=q[0])&(x<=q[2])&(y>=q[1])&(y<=q[3]);visible=owner&~hidden
    owner_distance=np.minimum.reduce([x-b[0],b[2]-x,y-b[1],b[3]-y])/2
    occluder_distance=np.hypot(np.maximum.reduce([q[0]-x,x-q[2],np.zeros_like(x)]),np.maximum.reduce([q[1]-y,y-q[3],np.zeros_like(y)]))/2
    endpoint=np.minimum(t,1-t)*np.linalg.norm(path[-1]-path[0])/2
    image_distance=np.minimum.reduce([uv[:,0]+.5,63.5-uv[:,0],uv[:,1]+.5,63.5-uv[:,1]])
    margin=cfg['margin_output_px'];eligible=visible&(owner_distance>=margin)&(occluder_distance>=margin)&(endpoint>=margin)&(image_distance>=margin)
    return uv,eligible,{'visible':visible,'owner_distance_px':owner_distance,'occluder_distance_px':occluder_distance,'endpoint_distance_px':endpoint,'image_distance_px':image_distance}

def frame_result(frame,geo):
    mesh,base,path,owners,segments=geo
    cam={**base,'eye':np.asarray(frame['eye']),'t':-np.asarray(frame['eye'])}
    before=hashlib.sha256(mesh['vertices'].tobytes()+mesh['faces'].tobytes()+path.tobytes()+np.asarray(owners).tobytes()+np.asarray(segments).tobytes()).hexdigest()
    start=time.monotonic();out=adapter.render_validated(mesh,owners,segments,path,candidate.render,cam,.8,2,2.,.006);seconds=time.monotonic()-start
    after=hashlib.sha256(mesh['vertices'].tobytes()+mesh['faces'].tobytes()+path.tobytes()+np.asarray(owners).tobytes()+np.asarray(segments).tobytes()).hexdigest()
    projected,bounds,extra,clean,raw,glob,high,quantized,final=analytic(frame)
    uv,eligible,detail=correspondence(projected,bounds,extra)
    a={'candidate_'+k:v for k,v in out.items()}
    a.update({'reference_'+k:v for k,v in clean.items()});a.update({'reference_raw_'+k:v for k,v in raw.items()})
    a.update(reference_high=high,reference_quantized_uint8=quantized,reference_final_uint8=final,known_uv=uv,eligible=eligible,world_path=path.copy(),world_vertices=mesh['vertices'].copy(),world_faces=mesh['faces'].copy(),camera_eye=cam['eye'],prescribed_projection=projected)
    a.update({'eligibility_'+k:v for k,v in detail.items()})
    valid={'immutable':before==after,'projection':float(abs(out['projected_path']-projected).max())<=1e-12,'reference_finite':all(np.isfinite(x).all() for x in raw.values()),'reference_partition':float(abs(raw['ribbon']-raw['visible']-raw['occluded']-raw['unsupported']).max())<=1e-10}
    for n in NAMES:valid['reference_integral_'+n]=abs(float(raw[n].sum())-glob[n])<=1e-8
    # Independent global closed-form mass for this full ribbon/vertical strip.
    length=float(np.linalg.norm(projected[-1]-projected[0]));hidden=(extra['bounds_high_xyxy'][2]-extra['bounds_high_xyxy'][0])*2*length/abs(projected[-1,0]-projected[0,0])
    expected={'ribbon':length*2,'owned':length*2,'occluded':hidden,'visible':length*2-hidden,'unsupported':0.}
    for n in NAMES:valid['reference_closed_form_'+n]=abs(float(raw[n].sum())-expected[n])<=1e-8
    gates={};errors={}
    for n in NAMES:
        err=out['raw_'+n]-raw[n];errors[n]={'max_abs':float(abs(err).max()),'L1':float(abs(err).sum()),'mass_abs':abs(float(err.sum()))}
        gates['raw_'+n]=errors[n]['max_abs']<=1e-10;gates['clean_'+n]=float(abs(out[n]-clean[n]).max())<=1e-10;gates['mass_'+n]=errors[n]['mass_abs']<=1e-8
    gates['quantized_exact']=np.array_equal(out['quantized_uint8'],quantized);gates['final_exact']=np.array_equal(out['final_uint8'],final)
    m={'frame':frame['frame'],'validity_gates':{k:bool(v) for k,v in valid.items()},'candidate_gates':{k:bool(v) for k,v in gates.items()},'area_errors':errors,'input_fingerprint':before,'total_samples':len(uv),'visible_samples':int(detail['visible'].sum()),'eligible_samples':int(eligible.sum()),'eligible_fraction_all':float(eligible.mean()),'eligible_fraction_visible':float(eligible.sum()/detail['visible'].sum()),'reference_masses':{k:float(v.sum()) for k,v in raw.items()}}
    return m,a,seconds

def regression():
    count=0;records=[];arrays=[];geo=old.geometry()
    for frame in old.P['trajectory']:
        m,a,_=old.frame_result(frame,geo)
        assert m==json.loads((c.P/'raw'/f'{frame["frame"]:04d}.json').read_text())
        with np.load(c.P/'raw'/f'{frame["frame"]:04d}.npz') as saved:
            assert set(saved.files)==set(a)
            for k in a:np.testing.assert_array_equal(a[k],saved[k]);count+=1
        records.append(m);arrays.append(a)
    report,a=old.sequence_report(records,arrays)
    with np.load(c.P/'raw/sequence.npz') as saved:
        assert set(saved.files)==set(a)
        for k in a:np.testing.assert_array_equal(a[k],saved[k]);count+=1
    prior=json.loads((c.P/'metrics.json').read_text())
    for key in ['temporal','controls','candidate_gates']:assert report[key]==prior[key]
    history=old.regression()
    assert history==json.loads((c.P/'REGRESSION.json').read_text())
    return {'round015_arrays_exact':count,'round015_temporal_control_metrics_exact':True,'history':history,'all_exact':count==496 and history['all_exact']}

def sequence_report(records,arrays):
    cfg=P['correspondence'];uv=np.array([a['known_uv'] for a in arrays]);eligible=np.array([a['eligible'] for a in arrays]);im=np.array([a['candidate_final_uint8'] for a in arrays]);ref=np.array([a['reference_final_uint8'] for a in arrays])
    d=np.asarray(P['case']['projected_path'][-1])-P['case']['projected_path'][0];normal=np.array([-d[1],d[0]])/np.linalg.norm(d)
    report,raw=metrics.compare(im,ref,uv,normal,eligible,cfg['profile_offsets'],cfg['presence_peak_min'])
    persistent=raw['persistent_eligible'];visible=np.array([a['eligibility_visible'] for a in arrays]);always_visible=visible.all(axis=0)
    report.update(persistent_visible_samples=int(always_visible.sum()),persistent_eligible_fraction_visible=float(persistent.sum()/always_visible.sum()),sample_world_length=float(np.linalg.norm(np.asarray(P['case']['path'][-1])-P['case']['path'][0])/cfg['samples']))
    controls={};control_arrays={}
    for name in ['reference_null','drift','dropout']:
        injected=ref.copy()
        if name=='drift':
            p=P['injections'][name];injected[p['frame']]=metrics.translated(injected[p['frame']],*p['shift_output_pixels'])
        if name=='dropout':injected[P['injections'][name]['frame']]=0
        r,a=metrics.compare(injected,ref,uv,normal,eligible,cfg['profile_offsets'],cfg['presence_peak_min'])
        if name=='reference_null':passed=r['full_frame_L1_uint8']==0 and r['extra_dropout_samples']==0 and r['extra_centroid_abs_px']['max']==0
        elif name=='drift':passed=r['full_frame_L1_uint8']>0 and r['extra_centroid_abs_px']['max'] is not None and r['extra_centroid_abs_px']['max']>.5
        else:
            f=P['injections'][name]['frame'];passed=r['full_frame_L1_uint8']>0 and r['frames'][f]['extra_missing_samples']==r['persistent_samples']>0
        controls[name]={'passed':bool(passed),'report':r};control_arrays[name+'_frames']=injected
    gates={'nonempty_eligibility':report['persistent_samples']>=cfg['min_persistent_samples'] and report['persistent_fraction_all_path']>=cfg['min_persistent_fraction'],'reference_profile_present':report['reference_all_persistent_present'],'all_frame_candidate_gates':all(all(r['candidate_gates'].values()) for r in records),'full_frame_exact':report['full_frame_max_uint8']==0,'temporal_residual_exact':report['temporal_residual_max_uint8']==0,'extra_centroid':report['extra_centroid_abs_px']['max'] is not None and report['extra_centroid_abs_px']['max']<=1e-12,'extra_motion':report['extra_normal_motion_max_px'] is not None and report['extra_normal_motion_max_px']<=1e-12,'no_extra_dropout':report['extra_dropout_samples']==0}
    report['projected_lengths_high_px']=[float(np.linalg.norm(a['prescribed_projection'][-1]-a['prescribed_projection'][0])) for a in arrays]
    report['occluded_fractions']=[r['reference_masses']['occluded']/r['reference_masses']['ribbon'] for r in records]
    report['nominal_screen_width_output_px']=P['style']['width_output_px']
    validity={'axial_projection_scale_and_occlusion_nonzero':bool(np.ptp(report['projected_lengths_high_px'])>0 and np.ptp(report['occluded_fractions'])>0),'screen_width_unchanged':P['style']['width_high_px']==2. and P['style']['width_output_px']==1.,'all_reference_gates':all(all(r['validity_gates'].values()) for r in records),'sensitivity_controls':all(x['passed'] for x in controls.values()),'nonempty_eligibility':gates['nonempty_eligibility'],'reference_profile_present':gates['reference_profile_present']}
    return {'temporal':report,'controls':controls,'candidate_gates':gates,'validity_gates':validity}, {**raw,**control_arrays,'candidate_frames':im,'reference_frames':ref}

def visuals(arrays):
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
    sheet=Image.new('RGB',(1000,60+4*310),'white');draw=ImageDraw.Draw(sheet)
    draw.text((12,8),'Fixed planar axial zoom | Analytic GT | All 12 full views',font=font,fill='black');draw.text((12,30),'Left: candidate. Right: independent reference. 64x64 output enlarged with nearest-neighbor.',font=font,fill='black')
    frames=[]
    for i,a in enumerate(arrays):
        panel=Image.new('RGB',(528,286),'white');d=ImageDraw.Draw(panel)
        d.text((5,4),f'Frame {i:02d} | Candidate',font=font,fill='black');d.text((268,4),'Independent reference',font=font,fill='black')
        for j,k in enumerate(['candidate_final_uint8','reference_final_uint8']):panel.paste(Image.fromarray(255-a[k]).resize((256,256),Image.Resampling.NEAREST).convert('RGB'),(j*264,26))
        frames.append(np.asarray(panel));panel.save(c.R/'frames'/f'{i:04d}.png')
        x=(i%3)*330;y=60+(i//3)*310;draw.text((x+4,y),f'Frame {i:02d} | eye z={P["trajectory"][i]["eye"][2]:.5f}',font=font,fill='black')
        for j,k in enumerate(['candidate_final_uint8','reference_final_uint8']):sheet.paste(Image.fromarray(255-a[k]).resize((152,152),Image.Resampling.NEAREST).convert('RGB'),(x+4+j*162,y+25))
        error=np.uint8(a['candidate_final_uint8']!=a['reference_final_uint8'])*255
        draw.text((x+4,y+184),'Any final mismatch (black)',font=font,fill='black');sheet.paste(Image.fromarray(255-error).resize((96,96),Image.Resampling.NEAREST).convert('RGB'),(x+110,y+205))
    sheet.save(c.R/'figures/full_view_contact_sheet.png')
    sys.path.insert(0,str(c.W/'.runtime_p0'));import imageio_ffmpeg
    exe=imageio_ffmpeg.get_ffmpeg_exe();video=c.R/'videos/axial_zoom.mkv'
    encode=[exe,'-hide_banner','-loglevel','error','-threads','2','-framerate','4','-i',str(c.R/'frames/%04d.png'),'-c:v','ffv1','-threads','2','-pix_fmt','bgr0','-y',str(video)]
    e=subprocess.run(encode,capture_output=True,timeout=60);assert e.returncode==0,e.stderr.decode()
    decode=[exe,'-hide_banner','-loglevel','error','-threads','2','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-threads','2','pipe:1']
    result=subprocess.run(decode,capture_output=True,timeout=60);assert result.returncode==0
    decoded=np.frombuffer(result.stdout,np.uint8).reshape(-1,286,528,3);expected=np.array(frames)
    np.testing.assert_array_equal(decoded,expected)
    hashes=[hashlib.sha256(x.tobytes()).hexdigest() for x in decoded];assert len(decoded)==12 and len(set(hashes))>=2
    scientific_distinct={k:len({hashlib.sha256(a[k].tobytes()).hexdigest() for a in arrays}) for k in ['candidate_final_uint8','reference_final_uint8']}
    assert min(scientific_distinct.values())>=2
    return {'scientific_distinct_frames_excluding_labels':scientific_distinct,'encode_argv':encode,'decode_argv':decode,'encode_returncode':e.returncode,'decode_returncode':result.returncode,'frames':12,'distinct_frames':len(set(hashes)),'decoded_exact_RGB':True,'frame_sha256':hashes,'ffmpeg_sha256':c.sha(exe),'note':'Lossless decode is integrity only; temporal evidence is independent image/correspondence comparison.'}

def evaluate():
    c.verify_lock();c.verify_prior();c.resources();assert not (c.R/'metrics.json').exists()
    for name in ['raw','figures','frames','videos']:(c.R/name).mkdir(exist_ok=True)
    c.status('evaluating_frozen_axial_zoom');start=time.monotonic();geo=geometry();records=[];arrays=[];timing=[]
    for f in P['trajectory']:
        c.resources();m,a,s=frame_result(f,geo);records.append(m);arrays.append(a);timing.append(s)
        c.write(c.R/'raw'/f'{f["frame"]:04d}.json',m);np.savez_compressed(c.R/'raw'/f'{f["frame"]:04d}.npz',**a)
        c.write(c.R/'PARTIAL_METRICS.json',{'completed_frames':len(records),'frames':records})
        print(json.dumps({'frame':f['frame'],'valid':all(m['validity_gates'].values()),'failed':[k for k,v in m['candidate_gates'].items() if not v]}),flush=True)
    report,raw=sequence_report(records,arrays);np.savez_compressed(c.R/'raw/sequence.npz',**raw)
    reg=regression();c.write(c.R/'REGRESSION.json',reg)
    video=visuals(arrays);c.write(c.R/'VIDEO_VALIDATION.json',video)
    tests=json.loads((c.R/'TESTS.json').read_text());report['validity_gates'].update(regression_exact=reg['all_exact'],tests_passed=tests['passed'],video_integrity=video['decoded_exact_RGB'])
    valid=all(report['validity_gates'].values());go=valid and all(report['candidate_gates'].values())
    out={**report,'frames':records,'complete':True,'measurement_valid':valid,'candidate_go':go,'verdict':'LIMITED_PLANAR_AXIAL_ZOOM_GO' if go else ('MEASUREMENT_VALID_AXIAL_ZOOM_NO_GO' if valid else 'ENGINEERING_INVALID'),'timing':{'render_seconds':timing,'render_median':float(np.median(timing)),'render_p95':float(np.percentile(timing,95)),'evaluation_seconds':time.monotonic()-start},'resources':c.resources(),'limits':P['limits']}
    c.write(c.R/'metrics.json',out);c.status('evaluated_awaiting_validation',scientific_verdict=out['verdict']);print(json.dumps({'verdict':out['verdict'],'candidate_gates':out['candidate_gates']}))

def validate():
    c.verify_lock();c.verify_prior();c.resources();saved=json.loads((c.R/'metrics.json').read_text());records=[];arrays=[];count=0;geo=geometry()
    for f in P['trajectory']:
        m,a,_=frame_result(f,geo);assert m==json.loads((c.R/'raw'/f'{f["frame"]:04d}.json').read_text())
        with np.load(c.R/'raw'/f'{f["frame"]:04d}.npz') as prior:
            assert set(a)==set(prior.files)
            for k in a:np.testing.assert_array_equal(a[k],prior[k]);count+=1
        records.append(m);arrays.append(a)
    report,a=sequence_report(records,arrays)
    with np.load(c.R/'raw/sequence.npz') as prior:
        assert set(a)==set(prior.files)
        for k in a:np.testing.assert_array_equal(a[k],prior[k]);count+=1
    for key in ['temporal','controls','candidate_gates']:assert report[key]==saved[key],key
    for key,value in report['validity_gates'].items():assert saved['validity_gates'][key]==value
    c.write(c.R/'VALIDATION.json',{'complete':True,'frames_exact':12,'arrays_exact':count,'temporal_control_metrics_exact':True,'prior_seal':c.verify_prior(),'resources':c.resources()});c.status('validated_awaiting_report');print(json.dumps({'arrays_exact':count,'verdict':saved['verdict']}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','evaluate','validate']);args=p.parse_args()
    try:globals()[args.command]()
    except Exception as e:c.status('interrupted_or_engineering_failure',execution_state='incomplete',scientific_verdict='ENGINEERING_INVALID',blockers=[type(e).__name__+': '+str(e)]);raise

"""Frozen independent readback, cold GS replay, and complete diagnostic media."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now,output_guard
from pathlib import Path
import argparse
import json
import subprocess
import numpy as np
from scipy import ndimage
from PIL import Image
from run_visibility_unit import protocol,match,asset,get_cache,fresh,locked,U1
from run_hybrid import read_npz,png,panel,array_hashes
from visibility_intervals import compare_visibility
from hybrid import compose,paper_copy,region_strength

FFMPEG=Path('/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01/.runtime_p0/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2')


def validate():
    p=protocol();m=match()
    for f,h in p['input_hashes'].items():assert sha(f)==h,f
    selection=read_npz(locked(p,U1/'results/lego/SELECTION.npz'))
    np.testing.assert_array_equal(selection['source_index'],np.arange(p['scene']['source_count']))
    assert int((selection['primary']>0).sum())==20122
    rows=[]
    for v in [x for x in p['views'] if x['kind']!='build']:
        c=v['camera'];folder=UNIT/v['kind']/c['view'];a=read_npz(folder/'FRAME.npz');e=json.loads((folder/'EVALUATION.json').read_text())
        for f,h in json.loads((folder/'COMPLETED.json').read_text())['files'].items():assert sha(folder/f)==h,f
        old=get_cache(p,v)
        for key in ('source','paper','support'):np.testing.assert_array_equal(a[key],old[key])
        np.testing.assert_array_equal(a['legacy_raw'],old['cross_raw'])
        np.testing.assert_array_equal(a['legacy_ink'],old['cross_ink'])
        t=read_npz(locked(p,v['trace']));ids=t['source_index'];assert np.all((ids>=0)&(ids<p['scene']['source_count']))
        np.testing.assert_allclose(t['weight'],t['alpha']*t['T'],rtol=0,atol=1e-14)
        mass=np.bincount(t['sample_index'],t['weight']*selection['primary'][ids],minlength=len(t['xy']))
        xy=t['xy'];np.testing.assert_allclose(mass,a['support'][xy[:,1],xy[:,0]],rtol=0,atol=1e-6)
        target=a['regions']==4;inner=ndimage.binary_erosion(target,iterations=2);near=ndimage.binary_dilation(target,iterations=2)
        domains=dict(target_full=target,target_interior=inner,boundary=near&~inner,far_other=(a['regions']>0)&~near,far_background=(a['regions']==0)&~near)
        samples=read_npz(folder/'SAMPLES.npz');xy=np.rint(samples['uv']).astype(int)
        ok=(xy[:,0]>=0)&(xy[:,1]>=0)&(xy[:,0]<a['support'].shape[1])&(xy[:,1]<a['support'].shape[0])
        support=np.zeros(len(xy),np.float32);support[ok]=a['support'][xy[ok,1],xy[ok,0]]
        for arm in ('legacy','interval'):
            for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
                key=arm+'_'+mode;alpha=a[arm+'_ink']*np.clip(a['support'],0,1)*scale
                predicted=a['paper']*(1-alpha[:,:,None])+.03*alpha[:,:,None]
                np.testing.assert_array_equal(alpha,a[key+'_alpha']);np.testing.assert_array_equal(predicted,a[key])
                raw=np.abs(a[key]-a['source']).sum(2);clipped=np.abs(np.clip(a[key],0,1)-np.clip(a['source'],0,1)).sum(2)
                for domain,mask in domains.items():
                    assert e['metrics'][key][domain]['pixels']==int(mask.sum())
                    np.testing.assert_allclose(e['metrics'][key][domain]['raw_L1_sum'],raw[mask].sum(),rtol=0,atol=1e-6)
                    np.testing.assert_allclose(e['metrics'][key][domain]['clipped_L1_sum'],clipped[mask].sum(),rtol=0,atol=1e-6)
                ink=np.abs(a[key]-a['paper']).sum(2)
                np.testing.assert_allclose(e['ink'][key]['target_visible_ink_L1'],ink[target].sum(),rtol=0,atol=1e-6)
                assert e['shape'][key]['visible']['pixels']==int(((alpha>.05)&target).sum())
                own=samples[arm+'_alpha']*support*scale;visible=samples['status']==0;weights=samples['length_weight']
                for label,mask in [('visible_supported_length',visible&(own>.05)),('visible_missing_length',visible&(own<=.05)),('occluded_supported_length',(~visible)&(own>.05))]:
                    np.testing.assert_allclose(e['attribution']['all'][key][label],weights[mask].sum(),rtol=0,atol=1e-8)
        rows.append(dict(kind=v['kind'],view=c['view'],cache_exact=True,original_ID_S_trace_verified=True,metrics_recomputed=True))
    js(UNIT/'VALIDATION.json',dict(utc=now(),views=rows,input_hashes_verified=len(p['input_hashes']),original_row_count=p['scene']['source_count'],selected_original_rows=20122,
        scope='Independent saved pixels, own-stroke aggregates, cache identity, actual original-ID alpha*T S; no independent physical proxy visibility GT.'))
    print('VALIDATED',len(rows),'records',len(p['input_hashes']),'inputs',flush=True)


def replay():
    import base_model as base
    from link_renderer import Renderer,validate_trace
    from membership import load_binding
    p=protocol();m=match();v=[x for x in p['views'] if x['kind']=='arc'][2];c=v['camera'];out=fresh(UNIT/'cold_replay_001')
    scene=p['scene'];a=base.load_source(scene['source']['original_ply'],scene['source']['sha256']);a['source_index']=np.arange(len(a['means']),dtype=np.int64)
    before=array_hashes(a);b,_=load_binding(scene['binding'],scene['source']['sha256'],scene['source_count']);strength=region_strength(b)
    selection=read_npz(locked(p,U1/'results/lego/SELECTION.npz'));np.testing.assert_array_equal(strength,selection['primary'])
    oldtrace=read_npz(locked(p,v['trace']));xy=oldtrace['xy'];renderer=Renderer(output_guard(out/'build'))
    source,tr=renderer.render(a,c,xy,strength);paper,_=renderer.render(paper_copy(a,c,strength,p['paper']),c)
    check=validate_trace(a,c,xy,source,tr);expected=read_npz(UNIT/'arc'/c['view']/'FRAME.npz')
    for key,value in [('source',source['rgb']),('paper',paper['rgb']),('support',source['contribution'])]:np.testing.assert_array_equal(value,expected[key])
    mesh,paths,meta=asset(p);r=compare_visibility(mesh,paths,meta['styles'],c)
    for arm in ('legacy','interval'):
        np.testing.assert_array_equal(r['ink'][arm],expected[arm+'_ink'])
        image,alpha=compose(paper['rgb'],r['ink'][arm],source['contribution'],True,m['scales'][arm])
        np.testing.assert_array_equal(image,expected[arm+'_matched']);np.testing.assert_array_equal(alpha,expected[arm+'_matched_alpha'])
        png(out/(arm+'_matched.png'),image)
    assert before==array_hashes(a)
    np.savez_compressed(out/'TRACE.npz',**tr,xy=xy)
    js(out/'REPLAY.json',dict(utc=now(),camera=c,source_render_calls=2,source_paper_S_both_inks_hybrids_alphas_exact=True,source_arrays_unchanged=True,source_array_hashes=before,trace=check))
    print('COLD REPLAY EXACT',c['view'],flush=True)


def media():
    p=protocol();out=fresh(UNIT/'media');images=[];labels=[]
    for v in [x for x in p['views'] if x['kind']=='dev']:
        a=read_npz(UNIT/'dev'/v['camera']['view']/'FRAME.npz')
        for key,label in [('source','Original GS'),('paper','Fixed original-GS paper'),('legacy_matched','Legacy / matched'),('interval_matched','Intervals / matched')]:
            images.append(a[key]);labels.append(v['camera']['view']+' | '+label)
    panel(UNIT/'ALL_DEV_VIEWS.png',images,labels,'All four exposed DEV views; original-GS paper + fixed cross proxy ink',columns=4)
    frames=[];images=[];labels=[]
    for i,v in enumerate([x for x in p['views'] if x['kind']=='arc']):
        c=v['camera'];a=read_npz(UNIT/'arc'/c['view']/'FRAME.npz');frame=out/f'frame_{i:03d}.png'
        panel(frame,[a[k] for k in ('source','legacy_matched','interval_matched')],['Original GS','Legacy / BUILD matched','Intervals / BUILD matched'],f'Actual camera arc {c["azimuth"]:.1f} deg; fixed geometry, paths and original IDs')
        frames.append(np.asarray(Image.open(frame).convert('RGB')))
        for key,label in [('legacy_matched','Legacy'),('interval_matched','Intervals')]:images.append(a[key]);labels.append(f'{c["azimuth"]:.1f} deg | '+label)
    panel(UNIT/'ALL_ARC_FRAMES.png',images,labels,'All nine actual cameras; exposed diagnostic, no independent temporal truth',columns=6)
    movie=out/'visibility_arc_ffv1.mkv'
    enc=[str(FFMPEG),'-v','error','-n','-threads','1','-framerate',str(p['fps']),'-i',str(out/'frame_%03d.png'),'-c:v','ffv1','-level','3','-threads','1',str(movie)]
    r=subprocess.run(enc,capture_output=True,timeout=60);r.check_returncode()
    dec=[str(FFMPEG),'-v','error','-threads','1','-i',str(movie),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','pipe:1']
    d=subprocess.run(dec,capture_output=True,timeout=60);d.check_returncode()
    expected=np.stack(frames);actual=np.frombuffer(d.stdout,np.uint8).reshape(expected.shape);assert np.array_equal(expected,actual)
    js(UNIT/'MEDIA_VALIDATION.json',dict(utc=now(),frames=9,all_frames_decoded_exact=True,encode_rc=r.returncode,decode_rc=d.returncode,encode_argv=enc,decode_argv=dec,movie_sha256=sha(movie)))
    print('MEDIA all nine frames decoded exact',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['validate','replay','media']);args=ap.parse_args()
    {'validate':validate,'replay':replay,'media':media}[args.stage]()

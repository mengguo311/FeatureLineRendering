#!/usr/bin/env python3
"""Offline report data only: aggregate existing diagnostics, never fit/render/rank."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'artifacts/hybrid_raster_trained_models_v1/transport'
OUT=ROOT/'out/hybrid_raster_trained_models_v1/transport'
SCENES=('hotdog','materials','mic','ship')
F=(1,14,27,41,53,67,79,93)
C=(7,21,33,47,59,73,86,99)
CHANNELS=('delta_D','delta_A','delta_N','delta_C','delta_G','visibility_raw')
PARAMETER_HASH='6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def read(path):return json.loads(Path(path).read_text())


def check_seal_envelope(directory,expected_context=None,consumed=()):
    """Envelope+inventory existence+consumed payload hashes; not full verifier."""
    directory=Path(directory);seal=read(directory/'SEAL.json')
    if directory.is_symlink() or not directory.is_dir():raise ValueError('not a real sealed directory')
    if sha(directory/'SEAL.json')!=(directory/'SEAL.sha256').read_text().strip():raise ValueError('seal checksum mismatch')
    if seal.get('schema')!='hybrid-raster-frame-v1':raise ValueError('seal schema mismatch')
    if canonical(seal['context'])!=seal['context_sha256']:raise ValueError('seal context checksum mismatch')
    if expected_context is not None and seal['context']!=expected_context:raise ValueError('seal context differs from manifest')
    actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() and p.name not in ('SEAL.json','SEAL.sha256')}
    if actual!=set(seal['files']):raise ValueError('seal inventory differs')
    for name in consumed:
        if name not in seal['files'] or sha(directory/name)!=seal['files'][name]:raise ValueError('consumed payload hash differs: '+name)
    return seal


def describe(values):
    values=[float(x) for x in values]
    return {'count':len(values),'sum':sum(values),'mean':float(np.mean(values)) if values else None,
            'min':min(values) if values else None,'max':max(values) if values else None}


def aggregate_group(frames):
    result={'frames':len(frames),'arms':{},'overlap':{},'B_only_argmax_counts':{k:0 for k in CHANNELS}}
    for arm in ('A','B','C'):
        rows=[f['diagnostics']['arms'][arm] for f in frames]
        result['arms'][arm]={'mass_per_frame':describe([x['mass'] for x in rows]),
            'support_per_frame':describe([x['support'] for x in rows]),'strata':{}}
        for stratum in ('background','outline','interior'):
            ss=[x['strata'][stratum] for x in rows];pixels=sum(x['pixels'] for x in ss);mass=sum(x['mass'] for x in ss);support=sum(x['support'] for x in ss)
            result['arms'][arm]['strata'][stratum]={'pixels':pixels,'mass':mass,'support':support,
                'mass_per_pixel':mass/pixels if pixels else None,'support_fraction':support/pixels if pixels else None}
    for key in ('A_only','B_only','shared','mass'):
        result['overlap'][key]=describe([f['diagnostics']['overlap'][key] for f in frames])
    for f in frames:
        for channel,count in f['B_only_argmax_counts'].items():result['B_only_argmax_counts'][channel]+=count
    total=sum(result['B_only_argmax_counts'].values())
    result['B_only_argmax_fractions']={k:v/total if total else None for k,v in result['B_only_argmax_counts'].items()}
    coverage=[f['diagnostics']['raw']['top4_coverage'] for f in frames]
    finite=[x for x in coverage if x['count'] and x['mean'] is not None];pixels=sum(x['count'] for x in finite)
    result['top4_coverage']={'foreground_definition':'alpha > .05, inherited diagnostics',
        'pixel_count':pixels,'pixel_weighted_mean':sum(x['mean']*x['count'] for x in finite)/pixels if pixels else None,
        'mean_of_frame_p05':float(np.mean([x['p05'] for x in finite])) if finite else None,
        'minimum_frame_p05':min(x['p05'] for x in finite) if finite else None,
        'global_min':min(x['min'] for x in finite) if finite else None,'global_max':max(x['max'] for x in finite) if finite else None,
        'quantile_disclosure':'mean/min of frame P05 are not pooled-pixel P05; no pooled quantile inferred'}
    return result


def expected_keys():
    return [f'F_{i:03d}' for i in F]+[f'C_{i:03d}' for i in C]+[f'arc0_{i:03d}' for i in range(33)]


def summarize_scene(scene,art=ART,out=OUT):
    result={'scene':scene,'expected_frames':49,'expected_raw_seals':49,'expected_frame_seals':49,
            'expected_videos':6,'expected_contacts':15,'expected_first_mid_last':9,'errors':[],'frames':[]}
    counts={'raw_seal_envelopes':0,'frame_seal_envelopes':0,'media_seal_envelopes':0,'videos':0,'contacts':0,'first_mid_last':0}
    path=art/scene/'FRAMES.json'
    if not path.is_file():
        result.update(status='MISSING_PRODUCTION',missing_keys=expected_keys(),counts=counts,groups={});return result
    manifest=read(path);result['frames_manifest_sha256']=sha(path);result['checkpoint']=manifest['checkpoint']
    records=manifest.get('records',[]);keys=[r['key'] for r in records]
    if len(keys)!=49 or set(keys)!=set(expected_keys()):result['errors'].append('manifest does not cover exact49 frames')
    result['missing_keys']=sorted(set(expected_keys())-set(keys))
    for record in records:
        key=record['key'];directory=out/'frames'/scene/key
        try:
            if key not in expected_keys():raise ValueError('frame key outside predeclared domain')
            seal=check_seal_envelope(directory,record['context'],('diagnostics.json','provenance.npz'))
            if sha(directory/'SEAL.json')!=record['seal_sha256']:raise ValueError('frame manifest seal digest differs')
            if seal['context'].get('scientific_parameter_hash')!=PARAMETER_HASH:raise ValueError('scientific parameter differs')
            counts['frame_seal_envelopes']+=1
            rawseal=check_seal_envelope(out/'raw'/scene/key,record['context']);counts['raw_seal_envelopes']+=1
            diagnostics=read(directory/'diagnostics.json')
            if diagnostics['parameter_hash']!=PARAMETER_HASH or diagnostics['frame']!=key:raise ValueError('diagnostic identity differs')
            if tuple(diagnostics['B_channel_order'])!=CHANNELS:raise ValueError('B channel order differs')
            with np.load(directory/'provenance.npz',allow_pickle=False) as data:
                mask=data['B_only'];argmax=data['B_argmax']
                if mask.shape!=argmax.shape or mask.dtype.kind!='b':raise ValueError('provenance shape/type differs')
                if np.any((argmax[mask]<0)|(argmax[mask]>=len(CHANNELS))):raise ValueError('B-only argmax outside channel domain')
                counts_b={channel:int(np.count_nonzero(mask&(argmax==i))) for i,channel in enumerate(CHANNELS)}
            if sum(counts_b.values())!=diagnostics['overlap']['B_only']:raise ValueError('B-only provenance count differs from diagnostics')
            result['frames'].append({'key':key,'split':diagnostics['split'],'diagnostics':diagnostics,'B_only_argmax_counts':counts_b,
                                     'diagnostics_sha256':sha(directory/'diagnostics.json'),'provenance_sha256':sha(directory/'provenance.npz')})
        except Exception as error:result['errors'].append(key+': '+str(error))
    result['groups']={split:aggregate_group([f for f in result['frames'] if f['split']==split]) for split in ('F','C','arc0')}
    result['groups']['all']=aggregate_group(result['frames'])
    media_path=art/scene/'MEDIA.json'
    if media_path.is_file():
        media=read(media_path);directory=out/'media'/scene
        try:
            check_seal_envelope(directory,consumed=('MANIFEST.json',));counts['media_seal_envelopes']=1
            if media!=read(directory/'MANIFEST.json'):raise ValueError('artifact MEDIA differs from sealed media manifest')
            counts.update(videos=len(media['videos']),contacts=len(media['contacts']),first_mid_last=len(media['first_mid_last']))
            result['media_manifest_sha256']=sha(media_path)
            result['media']={'videos':{k:{x:v.get(x) for x in ('path','sha256','frames','distinct_frames','size','fps','codec','pixel_format','faststart')} for k,v in media['videos'].items()},
                             'contacts':media['contacts'],'first_mid_last':media['first_mid_last']}
        except Exception as error:result['errors'].append('media: '+str(error))
    else:result['errors'].append('missing MEDIA.json')
    result['counts']=counts
    if counts!={'raw_seal_envelopes':49,'frame_seal_envelopes':49,'media_seal_envelopes':1,'videos':6,'contacts':15,'first_mid_last':9}:
        result['errors'].append('artifact expected counts not met')
    result['status']='COMPLETE_DIAGNOSTICS_ONLY' if not result['errors'] else 'PARTIAL_OR_INVALID'
    return result


def safe_summarize_scene(scene,art=ART,out=OUT):
    try:return summarize_scene(scene,art,out)
    except Exception as error:
        return {'scene':scene,'status':'PARTIAL_OR_INVALID','expected_frames':49,'frames':[],
                'errors':['aggregation aborted: '+type(error).__name__+': '+str(error)],
                'missing_keys':None,'counts':None,'groups':{},
                'disclosure':'Unreadable manifests prevent counting; existing files are preserved and are not declared absent.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--scenes',nargs='+',choices=SCENES,default=list(SCENES));parser.add_argument('--output',type=Path,default=ART/'DIAGNOSTIC_SUMMARY.json')
    args=parser.parse_args()
    result={'schema':'trained-transport-report-data-v1','scientific_parameter_hash':PARAMETER_HASH,'aggregator_sha256':sha(__file__),
        'scope':'只汇总已经完成的输出；墨量、支持与贡献覆盖不是有用线质量，不作通过门限、不调参、不加载数据集源图。',
        'seal_scope':'校验seal封套、文件清单存在性、所消费diagnostics/provenance/媒体manifest哈希；完整payload与视频解码由独立verifier完成，本文不冒充重复全检。',
        'C_disclosure':'C属于vanilla3DGS TRAIN，仅对NPR参数拟合留出；继承recipe在本轮从未重新拟合。',
        'human_review':'PENDING','scenes':{scene:safe_summarize_scene(scene) for scene in args.scenes}}
    result['complete_scenes']=[s for s,v in result['scenes'].items() if v['status']=='COMPLETE_DIAGNOSTICS_ONLY']
    result['actual_frames']=sum(len(v['frames']) for v in result['scenes'].values());result['expected_frames']=49*len(args.scenes)
    result['actual_frames_count_scope']='Successfully consumed diagnostically verified frames; may undercount existing files when an aggregation is invalid.'
    output=args.output;output.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+output.name+'.',dir=output.parent)
    with os.fdopen(fd,'w') as stream:json.dump(result,stream,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
    os.replace(name,output)
    print(json.dumps({'output':str(output),'actual_frames':result['actual_frames'],'expected_frames':result['expected_frames'],'complete_scenes':result['complete_scenes']},ensure_ascii=False))
    return 0 if len(result['complete_scenes'])==len(args.scenes) else 2

if __name__=='__main__':sys.exit(main())

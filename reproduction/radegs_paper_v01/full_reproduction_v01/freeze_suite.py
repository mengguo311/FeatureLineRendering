"""Freeze v2 table inventory, keeping unspecified author settings explicit.

No training dispatch. Candidate scenes are not silently promoted to paper fact.
"""
import collections
import csv
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image
import importlib.util

WORK=Path(__file__).resolve().parents[3]
HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
ART=WORK/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01'
CODE=WORK/'reproduction/radegs_paper_v01'
sys.path.insert(0,str(CODE/'stage2'))
from safety import atomic_json,sha256
C24='2d4bc087f1b4bd62c96054fbe89d273490526b81'
URL='https://github.com/HKUST-SAIL/RaDe-GS/blob/'+C24+'/'
PDF='https://arxiv.org/pdf/2406.01467v2'
SCANS=[24,37,40,55,63,65,69,83,97,105,106,110,114,118,122]

def main():
    assert not (ART/'FULL_SUITE_PROTOCOL.json').exists(),'frozen revision; write a new explicit revision to change it'
    source=HDD/'sources/RaDe-GS/scene/colmap_loader.py'
    spec=importlib.util.spec_from_file_location('colmap_audit',source)
    colmap=importlib.util.module_from_spec(spec);spec.loader.exec_module(colmap)
    data=json.loads((HDD/'stage2/state/DATA_STATUS.json').read_text())
    inventory={}
    for scan in SCANS:
        name=f'scan{scan}';p=HDD/'data/raw/dtu_original/DTU'/name
        images=sorted((p/'images').glob('*.png'));dimensions=collections.Counter()
        for image in images:
            with Image.open(image) as im:
                dimensions[(im.width,im.height,im.mode)]+=1;im.verify()
        ext=colmap.read_extrinsics_binary(p/'sparse/0/images.bin')
        intr=colmap.read_intrinsics_binary(p/'sparse/0/cameras.bin')
        assert len(ext)==len(images) and {v.name for v in ext.values()}=={i.name for i in images}
        inventory[name]={'raw_path':str(p),'files':sum(x.is_file() for x in p.rglob('*')),
            'image_count':len(images),'registered_camera_views':len(ext),'image_container_verify':'all PNG verify passed',
            'dimensions_modes':[{'width':k[0],'height':k[1],'mode':k[2],'count':v} for k,v in dimensions.items()],
            'camera_models':[{'model':v.model,'width':v.width,'height':v.height,'params':v.params.tolist()} for v in intr.values()],
            'camera_sha256':{f:sha256(p/'sparse/0'/f) for f in ['images.bin','cameras.bin','points3D.bin']},
            'original_raw_preserved':True,'prepared_copy':str(HDD/'data/prepared'/name) if (HDD/'data/prepared'/name).exists() else None,
            'metric_GT_role':'evaluation only','evaluation_GT_prepared':(HDD/f'data/eval_gt/dtu_eval_scan{scan}').exists()}
    atomic_json(ART/'FULL_DATA_STATUS.json',{'DTU':inventory,'archive_provenance':data['archive_provenance'],
        'other_datasets':'Stage1 inventory retained; no new TNT/Mip/Synthetic download this slice',
        'stage2_data_manifest':str(HDD/'stage2/state/DATA_STATUS.json'),'stage2_data_manifest_sha256':sha256(HDD/'stage2/state/DATA_STATUS.json')})
    entries=[]
    table1={'half20k':[.45,.74,.36,.39,.90,.73,.77,1.13,1.26,.66,.62,.83,.37,.61,.46],
            'half30k':[.46,.73,.33,.38,.79,.75,.76,1.19,1.22,.62,.70,.78,.36,.68,.47],
            'full30k':[.40,.71,.33,.37,.87,.79,.77,1.22,1.26,.70,.65,.85,.33,.66,.44]}
    for setting,values in table1.items():
        for scan,value in zip(SCANS,values):
            name=f'scan{scan}';iteration=20000 if setting=='half20k' else 30000;resolution=1 if setting=='full30k' else 2
            entries.append({'id':f'DTU_{name}_{setting}_TSDF','training_id':f'DTU_{name}_{setting}',
                'dataset':'DTU','scene':name,'paper_table':1,'paper_page':7,'paper_scope':'explicit table scene/row',
                'metric':{'name':'Chamfer_distance','unit':'mm','paper_value':value,'aggregation':'(mean_d2s+mean_s2d)/2; 15 scene macro mean'},
                'resolution_divisor':resolution,'resolution_pixels':[1554//resolution,1162//resolution],
                'iterations':iteration,'iterations_evidence':'explicit row' if setting!='full30k' else '30k inferred from global Section4.1.1; full-resolution row itself omits iterations',
                'schedule':None if iteration==20000 else {'photo':[1,15000],'geometry':[15001,30000]},
                'split':'all provided training views; no held-out claim','initialization':'provided COLMAP sparse points; never trained Gaussian PLY',
                'appearance':True,'extraction':'C24 TSDF + Marching Cubes; separate documented sparse-allocation engineering bridge if native stride4 has no sampled depth',
                'preprocess':'fresh prepared copy; C24 -r divisor; exact alpha-channel resize; mask only extraction/eval',
                'evaluation':'C24 evaluate_dtu_mesh.py and dtu_eval/eval.py with official DTU calibration/ObsMask/Plane/STL; biggest component/mask culling',
                'data_inventory_key':name,'sources':[PDF+'#page=7',URL+'README.md#L36-L45',URL+'mesh_extract.py#L20-L107',URL+'evaluate_dtu_mesh.py#L149-L214'],
                'unresolved':(['20k photometric/geometry boundary and LR horizon absent from paper/C24'] if iteration==20000 else []),
                'train_command_argv_template':None if iteration==20000 else ['<private-python>','train.py','-s','<prepared/'+name+'>','-m','<fresh-output>',
                    '-r',str(resolution),'--iterations','30000','--use_decoupled_appearance','--lambda_distortion','100','--lambda_depth_normal','5','--regularization_from_iter','15001'],
                'runtime_gate':'validated sealed runner integration required; template is not permission to bypass GPU gate'})
    tnt=['Barn','Caterpillar','Courthouse','Ignatius','Meetingroom','Truck']
    for extraction,values in [('TSDF',[.43,.26,.11,.73,.17,.53]),('marching_tetrahedra',[.43,.32,.21,.69,.25,.51])]:
        for scene,value in zip(tnt,values):
            entries.append({'id':f'TNT_{scene}_{extraction}','training_id':f'TNT_{scene}_30k','dataset':'TanksTemples','scene':scene,
                'paper_table':2,'paper_page':7,'paper_scope':'explicit table scene/row','metric':{'name':'F1','unit':'fraction_0_to_1','paper_value':value,'aggregation':'6 scene macro mean, separate extractors'},
                'resolution_divisor':None,'iterations':30000,'iterations_evidence':'global Section4.1.1',
                'schedule':{'photo':[1,15000],'geometry':[15001,30000]},'split':None,'initialization':'provided poses and COLMAP sparse cloud',
                'appearance':True,'extraction':extraction,'preprocess':'historical author GOF data pointer; verify original images/poses/scene mapping before execution',
                'evaluation':'official TNT poses/alignment/crop/laser cloud and scene tolerance; evaluation only',
                'sources':[PDF+'#page=7'],'unresolved':['v2 exact image resolution and holdout not specified','C24 lacks TNT extraction/eval entrypoints; source-pinned compatible bridge needed','official GT/poses/crop/alignment and tolerance not locally verified'],
                'train_command_argv_template':None})
    synth=[('mic',35.46),('chair',36.46),('ship',31.35),('materials',30.34),('lego',35.75),('drums',26.29),('ficus',35.37),('hotdog',37.76)]
    for scene,value in synth:
        entries.append({'id':f'SyntheticNeRF_{scene}_30k','training_id':f'SyntheticNeRF_{scene}_30k','dataset':'SyntheticNeRF','scene':scene,
            'paper_table':4,'paper_page':8,'paper_scope':'explicit table scene','metric':{'name':'PSNR','unit':'dB','paper_value':value,'aggregation':'8 scene macro mean'},
            'resolution_divisor':1,'resolution_pixels_candidate':[800,800],'iterations':30000,'iterations_evidence':'global Section4.1.1',
            'schedule':{'photo':[1,15000],'geometry':[15001,30000]},'split':'explicit transforms_train/test; expected 100/200 requires archive verification; val unused',
            'initialization':'C24 random100000 points in [-1.3,1.3]^3; fresh seed recorded, not vanilla checkpoint','appearance':False,
            'extraction':'not required for Table4','preprocess':'official NeRF Blender RGBA; original background composition requires provenance',
            'evaluation':'held-out test RGB PSNR; C24 lacks NVS exporter/evaluator','sources':[PDF+'#page=8',URL+'scene/dataset_readers.py#L274-L350'],
            'unresolved':['complete original train/test data not verified','author exact background choice not proven','C24-compatible heldout export/metric bridge missing'],
            'train_command_argv_template':None})
    for group,scenes,divisor in [('outdoor',['bicycle','flowers','garden','stump','treehill'],4),('indoor',['room','counter','kitchen','bonsai'],2)]:
        for scene in scenes:
            entries.append({'id':f'Mip360_{scene}_candidate','training_id':f'Mip360_{scene}_candidate','dataset':'MipNeRF360','scene':scene,
                'paper_table':3,'paper_page':7,'paper_scope':'candidate canonical dataset scene; paper names only indoor/outdoor aggregate','group':group,
                'metric':{'name':['PSNR','SSIM','LPIPS'],'unit':['dB','dimensionless','dimensionless'],'paper_value':None,'aggregation':'scene means then group macro mean; exact scene membership unresolved'},
                'resolution_divisor_candidate':divisor,'iterations':30000,'iterations_evidence':'global Section4.1.1',
                'schedule':{'photo':[1,15000],'geometry':[15001,30000]},'split_candidate':'sorted image_names, every8th test as C24 --eval; author use unproven',
                'initialization':'provided COLMAP sparse cloud','appearance':False,'extraction':'not required for Table3',
                'preprocess':'official 360_v2 + extra scenes; avoid double resampling images_4/images_2',
                'evaluation':'heldout RGB PSNR/SSIM/LPIPS; historical C25 VGG reference cannot change C24 training',
                'sources':[PDF+'#page=7','https://github.com/graphdeco-inria/gaussian-splatting/blob/54c035f7834b564019656c3e3fcc3646292f727d/full_eval.py#L15-L59'],
                'unresolved':['actual RaDe-v2 scene membership/resolution/split not explicitly released','dataset not acquired','C24-compatible heldout renderer/metric bridge missing'],
                'train_command_argv_template':None})
    groups=[{'table':1,'row':r,'paper_CD_mm':v,'paper_H800_minutes':t} for r,v,t in [('half20k',.69,5),('half30k',.68,8.3),('full',.69,20.2)]]
    groups += [{'table':2,'extractor':x,'paper_F1':v,'paper_H800_minutes':11.5} for x,v in [('TSDF',.37),('marching_tetrahedra',.40)]]
    groups += [{'table':3,'group':g,'paper_values':dict(zip(['PSNR_dB','SSIM','LPIPS'],v))} for g,v in [('outdoor',[25.17,.764,.199]),('indoor',[30.74,.928,.165])]]
    groups += [{'table':4,'paper_PSNR_dB':33.60}]
    protocol={'schema':1,'freeze_kind':'paper table inventory frozen; unresolved author settings are blocked, not silently guessed',
        'source_sha':C24,'paper':{'url':PDF,'sha256':'7940677b85007b76d0285fa87a5782ee7a8e060d5c8db526853743950a3c4f24'},
        'stage1_audit_sha256':sha256(ART.parent/'STAGE1_AUDIT_ZH.md'),
        'method':{'wd':100,'wn':5,'Eq23':'ordered camera-z double sum, alphaT weight-gradient detached; no NDC, M^-2, RGB edge weight',
            'Eq24':'sum alphaT_i*(1-n_i dot n_depth), unnormalized; no alpha/normal detach',
            'depth':'Eq4 affine camera-z; final median','filter':'C24 Mip3D','densification':'C24 GOF',
            'unmentioned_defaults':'C24 frozen with explicit paper_text_variant changes; image-mean reduction/central-difference borders engineering defaults',
            'not_bitexact_author_experiment':True,'latest_training_methods_excluded':['C25/C26 depth changes','PGSR','Objaverse']},
        'entries':entries,'reported_aggregates':groups,
        'completion_gate':['actual data/file/schema/hash verification','frozen executable protocol and source/native/config hashes','CPU and GPU derivative/forward gates',
            'fresh initialization and required unique iterations','required views exported and finite','nonempty finite mesh for geometry metrics',
            'official metric finite with verified units/masks and no training GT leakage','representative visual review','per-stage valid seals'],
        'negative_results':'record null metric/status/reason and retain failed evidence; never mark scientific reproduction complete for empty geometry',
        'dispatch_gate':'No new scene while scan24 training/geometry failure requires diagnosis. Single GPU0 shared policy; root>=10GiB/HDD>=50GiB; recheck per launch.',
        'storage':'no large downloads before current free-space/expanded-size budget; preserve datasets/completed models/evidence',
        'timing':'paper H800 timing is reference only; no A6000/shared-GPU timing equivalence',
        'ablation_scope':'v2 contains no separate ablation table; DTU20k/full rows and TNT two extractors retained. No invented loss arm, seed search or baseline-method retraining.',
        'qualitative_scope':'RGB/depth/normal/mesh diagnostics from actual experiments; paper Figures1,5-10 are qualitative comparisons, not permission for unlisted training variants'}
    atomic_json(ART/'FULL_SUITE_PROTOCOL.json',protocol)
    rows=[]
    for e in entries:
        pilot=e['id']=='DTU_scan24_half30k_TSDF'
        rows.append({'id':e['id'],'dataset':e['dataset'],'scene':e['scene'],'table':e['paper_table'],
            'status':'NEGATIVE_GEOMETRY_EMPTY_SURFACE' if pilot else ('BLOCKED_PROTOCOL_UNDERSPECIFIED' if e['unresolved'] else 'PENDING_SCAN24_DIAGNOSIS'),
            'train_verified':pilot,'export_verified':pilot,'metric_value':None,'paper_value':e['metric']['paper_value'],
            'metric_unit':e['metric']['unit'],'delta':None,'scientificdone':False,
            'reason':'0 supported TSDF crossing cubes at original thresholds; official CD undefined' if pilot else '; '.join(e['unresolved']) or 'scan24 diagnosis gate'})
    atomic_json(ART/'METRICS.json',{'protocol_sha256':sha256(ART/'FULL_SUITE_PROTOCOL.json'),'rows':rows,'all_complete':False})
    with (ART/'METRICS.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    confirmed=[e for e in entries if e['dataset']!='MipNeRF360']
    counts={'evaluation_rows':len(entries),'explicit_paper_scene_rows':len(confirmed),'candidate_Mip_scene_rows':len(entries)-len(confirmed),
        'training_ids_from_explicit_scene_rows':len({e['training_id'] for e in confirmed}),
        'conditional_training_ids_including_unconfirmed_Mip':len({e['training_id'] for e in entries}),
        'by_dataset':dict(collections.Counter(e['dataset'] for e in entries)),
        'metrics_rows_written':len(rows),'completed_full_chains':0,'finite_actual_metrics':0,
        'protocol_sha256':sha256(ART/'FULL_SUITE_PROTOCOL.json'),'not_a_claim_of_68_author_confirmed_experiments':True}
    assert len(rows)==len(entries)==len(set(e['id'] for e in entries))
    atomic_json(ART/'SUITE_COUNTS.json',counts)
    print(json.dumps(counts))

if __name__=='__main__':main()

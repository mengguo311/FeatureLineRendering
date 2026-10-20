"""Read-only cross-model original-row label comparison in 3 CPU-rendered views."""
import json,os,sys
from pathlib import Path
import numpy as np
from transfer import source_asset,cameras,sha256,ROOT,NATIVE_CODE,best_axis_null

for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[k]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
if hasattr(os,'sched_setaffinity'):
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
sys.path.insert(0,str(NATIVE_CODE))
from format import activate
from renderer import render
from PIL import Image,ImageDraw

def image(x):return Image.fromarray(np.uint8(np.clip(x,0,1)*255+.5),'RGB')

def main(scene,folder):
    from threadpoolctl import threadpool_limits
    threadpool_limits(2)
    folder=Path(folder)
    summary=json.loads((folder/'SUMMARY.json').read_text())
    if summary['status']!='CPU_RENDERED_EXPLORATORY_NOT_SEMANTICALLY_VALIDATED' or summary['scene']!=scene:
        raise ValueError('incomplete scene or ID mismatch')
    source,raw=source_asset(scene)
    if summary['source_sha256']!=sha256(source):raise ValueError('source mismatch')
    a=activate(raw.copy())
    xyz=a['means']
    def load(name):
        file=folder/(name+'_labels.npy')
        expected=(summary['partfield']['labels_sha256'] if name=='partfield' else summary['arms'][name]['labels_sha256'])
        if sha256(file)!=expected:raise ValueError('label hash mismatch')
        labels=np.load(file,allow_pickle=False)
        if labels.shape!=(len(xyz),):raise ValueError('row count mismatch')
        return labels
    pf=load('partfield');g=load('G_xyz');fusion=load('I_fusion_xyz_sh_projected')
    chosen=int(summary['selected_cluster'])
    target=pf==chosen
    null=best_axis_null(xyz,target)
    variants=[('PartField '+str(chosen),target),('axis '+null['axis']+' '+null['side'],null['mask'])]
    comps={}
    for title,labels in [('XYZ K3',g),('fusion K3',fusion)]:
        scores=[]
        for k in range(3):
            mask=labels==k
            intersection=int((mask&target).sum())
            iou=intersection/int((mask|target).sum())
            scores.append((iou,k,intersection))
        score,k,intersection=max(scores)
        variants.append((title+' '+str(k),labels==k))
        comps[title]={'selected_cluster':k,'intersection_original_rows':intersection,
            'jaccard_to_preselected_PartField_cluster':float(score),
            'rows':int((labels==k).sum()),'note':'Post-hoc source-ID match only, not semantic truth'}
    out={'status':'CROSS_MODEL_ORIGINAL_KERNEL_OFF_DIAGNOSTIC_NOT_SEMANTIC_EDIT',
         'scene':scene,'source_sha256':summary['source_sha256'],
         'selected_partfield_cluster':chosen,'match_to_parameter_arms':comps,'views':{}}
    for view in ('train_r_79','test_r_14','test_r_79'):
        c=cameras(scene,400)[view]
        r=render(a,c,background=(1,1,1),floor=.3)
        native=(ROOT/'training'/scene/'seed_1729/quality/measurements/native'/
           (('train_' if view.startswith('train') else 'val_')+view.split('_')[-1].zfill(3)+'.npz'))
        if not native.exists():raise FileNotFoundError(str(native))
        with np.load(native,allow_pickle=False) as d:
            expected=d['rgb_1']
            roi=d['roi']
            calib={'full_rgb_mae':float(np.mean(np.abs(r['rgb']-expected))),
                   'roi_rgb_mae':float(np.mean(np.abs(r['rgb'][roi]-expected[roi]))),
                   'native_reference_sha256':sha256(native),'roi_pixels':int(roi.sum())}
        sheet=Image.new('RGB',(400*(1+len(variants)),430),'white')
        draw=ImageDraw.Draw(sheet)
        sheet.paste(image(r['rgb']),(0,30));draw.text((8,6),'ORIGINAL',fill='black')
        vals=[]
        for j,(name,mask) in enumerate(variants,1):
            b=dict(a);b['opacity']=a['opacity'].copy();b['opacity'][mask]=0
            rr=render(b,c,background=(1,1,1),floor=.3)
            sheet.paste(image(rr['rgb']),(400*j,30));draw.text((400*j+8,6),name+' OFF',fill='black')
            delta=np.abs(rr['rgb']-r['rgb'])
            vals.append({'candidate':name,'removed_original_rows':int(mask.sum()),
                  'mae_vs_original':float(delta.mean()),
                  'changed_pixel_fraction_gt_0p05':float(np.mean(np.max(delta,axis=2)>.05))})
        file=folder/(view+'_parameter_comparison.png')
        if file.exists():raise FileExistsError(str(file))
        sheet.save(file)
        out['views'][view]={'native_calibration':calib,'cuts':vals,'image_sha256':sha256(file),'image':file.name}
        print('VIEW_DONE',scene,view,calib,flush=True)
        (folder/'PARAMETER_COMPARISON.json').write_text(json.dumps(out,indent=2)+'\n')
    print('COMPARE_DONE',scene,comps,flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--scene',required=True);p.add_argument('--folder',required=True)
    args=p.parse_args();main(args.scene,args.folder)

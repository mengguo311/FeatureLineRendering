"""Execute unchanged C24 evaluation on a separate CPU-TSDF result directory.

Only launched through the GPU0 shared low-load gate. No training, renderer
change, threshold selection or GT-based parameter selection. Exit status alone
is insufficient because upstream uses os.system for the inner DTU evaluator.
"""
import argparse,json,os,subprocess,sys,math
from pathlib import Path
from safety import atomic_json,sha256,verify_seal,seal_stage
from gpu_stages import report

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args()
    c=json.loads(Path(args.config).read_text())
    assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
    parent=json.loads(Path(c['parent_config']).read_text())
    for stage in ['train','export']:assert verify_seal(Path(parent['state_dir'])/(stage+'.seal.json'),stage,parent['inputs'])
    tsdf=json.loads(Path(c['tsdf_seal']).read_text())
    assert verify_seal(c['tsdf_seal'],'tsdf',tsdf['inputs'])
    assert all(sha256(p)==s for p,s in c['immutable_files'].items())
    # Limit only this task's own CPU affinity; no foreign process affected.
    cpus=sorted(os.sched_getaffinity(0))[:4];os.sched_setaffinity(0,cpus)
    directory=Path(c['evaluation_model'])
    completed=subprocess.run(c['official_eval_command'],cwd=c['cwd'],check=False)
    atomic_json(directory/'invocation.json',{'command':c['official_eval_command'],'cwd':c['cwd'],
        'returncode':completed.returncode,'own_CPU_affinity':cpus,'unchanged_author_evaluator':True,
        'upstream_random_shuffle_is_unseeded_default_rng':True,'GT_role':'evaluation only'})
    assert completed.returncode==0,'official evaluation process failed'
    metric=directory/'vis/results.json';values=json.loads(metric.read_text())
    assert all(math.isfinite(values[k]) and values[k]>=0 for k in ['mean_d2s','mean_s2d','overall']),values
    assert abs(values['overall']-(values['mean_d2s']+values['mean_s2d'])/2)<1e-10
    import open3d as o3d,numpy as np
    details=[]
    for name in ['recon.ply','recon_culled.ply','recon_aligned.ply']:
        mesh=o3d.io.read_triangle_mesh(str(directory/name));v=np.asarray(mesh.vertices)
        assert len(v) and len(mesh.triangles) and np.isfinite(v).all()
        details.append({'file':name,'vertices':len(v),'triangles':len(mesh.triangles),'bounds':[v.min(0).tolist(),v.max(0).tolist()]})
    outputs=[directory/n for n in ['recon.ply','recon_culled.ply','recon_aligned.ply','vis/results.json','invocation.json']]
    details={'metrics_mm':values,'meshes':details,'official_eval_executed':True,'scientificdone':False,
        'claim':'single corrected paper-text scan24; severe sparse reconstruction, not paper-value agreement'}
    result=directory/'evaluation_verified.json';atomic_json(result,details);outputs.append(result)
    seal_stage(directory/'eval.seal.json','eval',c['inputs'],outputs)
    report(c,'checkpoint_diagnostic',outputs+[directory/'eval.seal.json'],details)

if __name__=='__main__':main()

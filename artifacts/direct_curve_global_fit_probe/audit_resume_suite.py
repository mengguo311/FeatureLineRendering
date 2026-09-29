"""Read-only audit of the unchanged-suite harness, using existing audited parser."""
import json,sys
from pathlib import Path
from src.corrected_audit import audit_policy
from scripts.verify_direct_curve_probe import sha
root=Path.cwd();out=root/'out/direct_curve_global_fit_probe';up=root/'out/multiscene_foundation/vendor/gaussian-splatting'
readonly=[root/'src',root/'scripts',root/'tests',root/'artifacts/direct_curve_global_fit_probe',Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys'),Path('/home/u00134/bin/miniconda3/envs/ts_diffusion/lib'),root/'out/vrss/vendor/official_site',*[up/k for k in ['gaussian_renderer','scene','utils','arguments','.git']],Path('/home/u00134/.cache/matplotlib/fontlist-v390.json'),Path('/home/u00134/.gitconfig'),root/'out/multiscene_foundation/config.json',root/'out/point_feature_foundation/setup/composite.so',root/'out/multiscene_foundation/setup/layers.so',*[root/'out/multiscene_foundation_corrected/setup'/k for k in ['area_layers.so','fast_query.so','surface.so']],*[root/'out/density_ridge_lines'/f'{s}_ridge_grids.npz' for s in ['lego','chair','drums','ficus']],root/'out/topk_layered_probe/setup/topk_native.so',out/'setup/quantiles.so',out/'setup/quantiles_cuda_v1.so',out/'setup/stock_oracle_v1.so']
policy=dict(readonly=[str(p) for p in readonly],writable=['/tmp','/dev'])
trace=Path(sys.argv[1]) if len(sys.argv)>1 else out/'setup/full_suite_resume_226.strace';result=audit_policy(trace.read_text(),policy,out/'setup',[str(root),str(up)])
result['trace_sha256']=sha(trace)
target=Path(sys.argv[2]) if len(sys.argv)>2 else root/'artifacts/direct_curve_global_fit_probe/SUITE_ACCESS_AUDIT_RESUME_226.json'
with target.open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['passed','forbidden_successes','unparsed_open_lines','trace_sha256']},indent=2));sys.exit(0 if result['passed'] else 1)

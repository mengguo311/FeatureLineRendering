"""Stream four original SH3 camera units, atomically seal their native evidence."""
import argparse
import gc
import json
import os
from pathlib import Path
import shutil
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from runtime import ART, EXP, OUT, ROOT, SOURCE, atomic_json, digest, guard, sha, source_hashes
from native import load_backend
from scene_io import freeze_cameras, load_model, make_settings
from benchmark import run_benchmark
import numpy as np
from PIL import Image
import torch

def save_npy(path, tensor):
    np.save(path, tensor.detach().cpu().numpy(), allow_pickle=False)

def save_rgb(path, tensor):
    rgb = tensor.detach().permute(1, 2, 0).cpu().numpy()
    Image.fromarray(np.clip(rgb*255, 0, 255).astype(np.uint8)).save(path)

def camera_unit(name, record, camera, model, modules, freeze, do_benchmark=True):
    unit = name + '_r_' + str(camera['index']).zfill(3)
    guard('camera_' + unit)
    destination = OUT / 'views' / unit
    sealpath = ART / 'seals' / (unit + '.json')
    settings = {k: make_settings(m, camera) for k,m in modules.items()}
    dependencies = ['build.py', 'native.patch', 'protocol.json', 'run_real.py',
                    'src/runtime.py', 'src/native.py', 'src/scene_io.py', 'src/benchmark.py']
    config = dict(camera=camera, checkpoint_sha256=record['model_sha256'],
                  source_hashes={str((EXP/p).relative_to(ROOT)):sha(EXP/p) for p in dependencies},
                  build_sha256=sha(ART/'BUILD.json'),
                  protocol_sha256=sha(EXP/'protocol.json'), benchmark=do_benchmark)
    config_sha = digest(config)
    if sealpath.exists():
        old = json.loads(sealpath.read_text())
        if old['config_sha256'] != config_sha:
            raise RuntimeError('sealed camera unit config changed; use a fresh run path')
        for path, expected in old['files'].items():
            if sha(ROOT/path) != expected:
                raise RuntimeError('sealed camera output changed')
        print('SEALED_SKIP', unit, flush=True)
        return json.loads((ART/'results'/ (unit + '.json')).read_text())
    if destination.exists():
        raise RuntimeError('unsealed evidence already exists; preserve and inspect it')
    tmp = destination.with_name(destination.name + '.partial_' + str(time.time_ns()))
    tmp.mkdir(parents=True)
    def call(backend, K=None):
        opts = dict(attribution=True, K=K) if K else {}
        return modules[backend].GaussianRasterizer(settings[backend])(**model, **opts)
    try:
        with torch.no_grad():
            baseline, radii = call('actual'); isolated, isolated_radii = call('original')
            off, off_radii = call('patched'); on = call('patched', 8)
            torch.cuda.synchronize()
            rgb_checks = {}
            for label, rgb, rad in [('isolated_original', isolated, isolated_radii),
                                  ('debug_off', off, off_radii), ('debug_on', on.rgb, on.radii)]:
                error = float((rgb-baseline).abs().max())
                exact = bool(torch.equal(rgb, baseline) and torch.equal(rad, radii))
                rgb_checks[label] = dict(bitwise_equal=exact, max_abs_rgb_error=error)
                if not exact:
                    raise AssertionError('stock RGB/radii changed: ' + label + ' error=' + str(error))
            alpha, total = on.accumulated_alpha, on.all_contribution_sum
            error = float((total-alpha).abs().max())
            tol = json.loads((EXP/'protocol.json').read_text())['absolute_fp32_tolerance']
            if not torch.isfinite(total).all() or not torch.isfinite(on.final_T).all() or error > tol:
                raise AssertionError('all accepted weights vs 1-T error=' + str(error))
            if not bool(torch.all(on.gaussian_weights[..., 1:] <= on.gaussian_weights[..., :-1])):
                raise AssertionError('unsorted weights')
            if not bool(torch.all((on.gaussian_ids >= -1) & (on.gaussian_ids < record['count']))):
                raise AssertionError('IDs outside original model rows')
            mass = on.gaussian_weights.sum(-1)
            missing = alpha - mass
            coverage = torch.where(alpha > 0, mass / alpha.clamp_min(1e-30), torch.zeros_like(alpha))
            foreground = alpha > 0
            for label,tensor in [('baseline_rgb',baseline), ('patched_off_rgb',off), ('patched_on_rgb',on.rgb)]:
                save_rgb(tmp/(label+'.png'), tensor); save_npy(tmp/(label+'.npy'),tensor)
            for label,tensor in [('topk_ids',on.gaussian_ids), ('topk_weights',on.gaussian_weights),
                                 ('all_contribution_sum',total), ('final_T',on.final_T),
                                 ('alpha',alpha), ('coverage',coverage), ('missing_mass',missing)]:
                save_npy(tmp/(label+'.npy'),tensor)
            for label,tensor in [('alpha',alpha), ('coverage',coverage)]:
                Image.fromarray(np.clip(tensor.cpu().numpy()*255,0,255).astype(np.uint8)).save(tmp/(label+'.png'))
            ids = on.dominant_id.cpu().numpy()
            h = (ids.astype(np.uint64)+1) * np.uint64(2654435761)
            rgb_ids = np.stack([(h >> shift) & 255 for shift in (0,8,16)], axis=-1).astype(np.uint8)
            rgb_ids[ids < 0] = 255
            Image.fromarray(rgb_ids).save(tmp/'dominant_id.png')
            # Compact panel only; all 800x800 numerical data stay in ignored output.
            panel = Image.new('RGB', (4*400,400))
            for i,f in enumerate(('baseline_rgb.png','dominant_id.png','alpha.png','coverage.png')):
                with Image.open(tmp/f) as im:
                    panel.paste(im.convert('RGB').resize((400,400)), (i*400,0))
            panel.save(tmp/'panel.png')
            checks = dict(rgb=rgb_checks, sum_all_vs_alpha_max_error=error,
                finite=True, sorted_weights=True, original_row_ids=True,
                foreground_pixels=int(foreground.sum()), background_pixels=int((~foreground).sum()),
                coverage_mean_positive_alpha=float(coverage[foreground].mean()),
                coverage_p05_positive_alpha=float(torch.quantile(coverage[foreground], .05)),
                missing_mass_mean=float(missing.mean()), missing_mass_max=float(missing.max()),
                alpha_sum=float(alpha.sum()), topk_mass_sum=float(mass.sum()),
                global_mass_coverage=float(mass.sum()/alpha.sum()))
            del baseline, isolated, off, on, radii, isolated_radii, off_radii, alpha, total, mass, missing, coverage, foreground
            gc.collect(); torch.cuda.synchronize()
            benchmarks = []
            if do_benchmark:
                for label, backend, K in [('actual_stock','actual',None), ('isolated_original','original',None),
                    ('debug_off','patched',None)] + [('K'+str(k),'patched',k) for k in (1,4,8,16)]:
                    print('BENCHMARK', unit, label, flush=True)
                    benchmarks.append(run_benchmark(lambda b=backend,k=K: call(b,k), unit+'_'+label, attribution=K is not None))
            # Seal the completed camera as an atomic directory batch.
            save_config = dict(config=config, config_sha256=config_sha, source_freeze=freeze['data_freeze_sha256'])
            atomic_json(tmp/'MANIFEST.json', save_config)
        os.replace(tmp, destination)
        # Keep a reviewable small figure in tracked artifacts.
        panelpath=ART/'figures'/(unit+'.png'); panelpath.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(destination/'panel.png',panelpath)
        result = dict(unit=unit, scene=name, gaussian_count=record['count'], camera_sha256=camera['camera_sha256'],
                      resolution=[800,800], sh_degree=3, K=8, depth='NOT_AVAILABLE',
                      checks=checks, benchmarks=benchmarks, config_sha256=config_sha,
                      output_path=str(destination.relative_to(ROOT)))
        resultpath=ART/'results'/(unit+'.json'); atomic_json(resultpath,result)
        files=[p for p in destination.rglob('*') if p.is_file()]+[resultpath,panelpath]
        atomic_json(sealpath,dict(config_sha256=config_sha,files={str(p.relative_to(ROOT)):sha(p) for p in files},status='COMPLETE'))
        print('COMPLETE',unit,json.dumps(checks),flush=True)
        return result
    except Exception as e:
        atomic_json(ART/'failures'/(unit+'_'+str(time.time_ns())+'.json'),dict(unit=unit,error=str(e),partial_evidence=str(tmp)))
        raise

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--no-benchmark',action='store_true');args=parser.parse_args()
    guard('real_start'); torch.set_num_threads(2)
    freeze=freeze_cameras(); modules={k:load_backend(k) for k in ('actual','original','patched')}
    results=[]
    for name,record in freeze['scenes'].items():
        guard('load_model_'+name)
        model=load_model(record)
        for camera in record['cameras']:
            results.append(camera_unit(name,record,camera,model,modules,freeze,not args.no_benchmark))
        del model;gc.collect();torch.cuda.synchronize()
    atomic_json(ART/'results/REAL_SUMMARY.json',dict(passed=True,units=[r['unit'] for r in results],
                                                  protected_after={p:sha(p) for p in json.loads((ART/'PROTECTED_BEFORE.json').read_text())}))

if __name__=='__main__':
    main()

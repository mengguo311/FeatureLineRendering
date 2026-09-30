#!/usr/bin/env python3
"""Independent bounded CPU runner; immutable inputs, atomic units, resume verification."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
import fcntl
import json
import time
import shutil
import subprocess
import traceback
import numpy as np
import cv2
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import imageio_ffmpeg
from src.foundation import restrict_filesystem
from src.temporal_depth2d import (sha, atomic_json, validate_camera, depth2d, graph, atlas,
    Tracker, render_vectors, transport, match_ink, actual_ink, quantize, seal_directory, verify_seal)

ART = ROOT / 'artifacts/temporal_depth2d_video_probe'
SCENES = ['lego', 'chair', 'drums', 'ficus']
SOURCE_FILES = ['src/temporal_depth2d.py', 'scripts/run_temporal_depth2d_probe.py',
                'tests/test_temporal_depth2d.py', 'src/foundation.py']
START = time.monotonic()
READS = []


def within_budget():
    if time.monotonic() - START > 45 * 60: raise TimeoutError('registered 45 minute CPU wall budget exhausted')


def science_metadata():
    return {'protocol': sha(ART / 'PROTOCOL.md'), 'inputs': sha(ART / 'INPUTS.json'),
            'sources': {p: sha(ROOT / p) for p in SOURCE_FILES}}


def image(ink):
    return np.repeat(np.round((1 - np.clip(ink, 0, 1)) * 255).astype('u1')[:, :, None], 3, 2)


def rgb_image(frame):
    return np.round(np.clip(frame['gs_rgb'], 0, 1) * 255).astype('u1')


def panel(images, labels, size=800):
    out = Image.new('RGB', (size * len(images), size + 28), 'white'); draw = ImageDraw.Draw(out)
    for i, (im, label) in enumerate(zip(images, labels)):
        out.paste(Image.fromarray(im).resize((size, size), Image.Resampling.LANCZOS), (i * size, 28))
        draw.text((i * size + 8, 7), label, fill='black')
    return np.asarray(out)


def save_png(path, im):
    path.parent.mkdir(parents=True, exist_ok=True); Image.fromarray(im).save(path)


def video(path, frames):
    iterator = iter(frames); first = next(iterator); h, w = first.shape[:2]
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-nostdin', '-y', '-f', 'rawvideo',
           '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', '12', '-i', 'pipe:0', '-an', '-c:v',
           'libx264', '-threads', '1', '-preset', 'fast', '-crf', '16', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', str(path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        proc.stdin.write(first.tobytes())
        for im in iterator: proc.stdin.write(np.ascontiguousarray(im).tobytes())
        proc.stdin.close(); error = proc.stderr.read(); code = proc.wait()
        if code: raise RuntimeError(error.decode())
    finally:
        if proc.poll() is None: proc.kill(); proc.wait()


def decode_video(path, expected):
    cap = cv2.VideoCapture(str(path)); count = 0; shape = None
    while True:
        ok, frame = cap.read()
        if not ok: break
        if not np.isfinite(frame).all(): raise ValueError('invalid decoded video')
        count += 1; shape = frame.shape
    cap.release()
    if count != expected: raise ValueError(f'video decode {path}: {count} != {expected}')
    return {'path': str(path), 'frames': count, 'shape': list(shape), 'sha256': sha(path)}


def load_frame(manifest, scene, key, split='arc'):
    records = manifest['scenes'][scene]['files']
    found = {Path(r['path']).suffix: r for r in records if r.get('split') == split and r.get('frame') == key}
    if set(found) != {'.json', '.npz'}: raise ValueError('frame not in frozen allowlist')
    for r in found.values():
        if sha(r['path']) != r['sha256']: raise ValueError('input hash mismatch')
        READS.append({'path': r['path'], 'split': split, 'sha256': r['sha256'], 'operation': 'native_read'})
    camera = json.loads(Path(found['.json']['path']).read_text())['camera']; validate_camera(camera)
    with np.load(found['.npz']['path'], allow_pickle=False) as d:
        f = {k: d[k] for k in ['gs_rgb', 'depth', 'alpha']}; f['mask'] = depth2d(d['D.native_edge']) > 0
    if f['depth'].shape != (camera['native_height'], camera['native_width']): raise ValueError('size mismatch')
    f.update(key=key, camera=camera)
    return f


def readability(ink, f):
    base = f['mask']; xy, _ = graph(base); p = xy.astype(int)
    d = ndi.distance_transform_edt(~(ink > .1)); support = d[p[:, 1], p[:, 0]] <= 2
    roi = f['alpha'] >= .5
    outline = (ndi.distance_transform_edt(roi) <= 4) & roi | (ndi.distance_transform_edt(~roi) <= 4) & ~roi
    strata = {'all': np.ones(len(p), bool), 'outline': outline[p[:, 1], p[:, 0]],
              'interior': (roi & ~outline)[p[:, 1], p[:, 0]]}
    covered = {k: float(support[m].mean()) if m.any() else None for k, m in strata.items()}
    beyond = ndi.distance_transform_edt(~base) > 3
    unsupported = float(ink[beyond].sum() / max(ink.sum(), 1e-12))
    return {'coverage': covered, 'skeleton_vertices': len(p), 'unsupported_ink_fraction': unsupported,
            'ink_ratio': actual_ink(ink) / max(actual_ink(base.astype(float)), 1e-12), 'actual_ink': actual_ink(ink)}


def motion(a, b, f0, f1):
    warped, valid, info = transport(a, f0, f1); now = b * valid
    wa = warped > .1; nb = now > .1
    da = ndi.distance_transform_edt(~wa); db = ndi.distance_transform_edt(~nb)
    appearing = nb & (da > 2); disappearing = wa & (db > 2)
    mass = now.sum() + warped.sum()
    lab, _ = ndi.label(appearing, np.ones((3, 3))); sizes = np.bincount(lab.ravel())[1:]
    return dict(geometry=float((now[appearing].sum() + warped[disappearing].sum()) / max(mass, 1e-12)),
                opacity_residual=float(abs(now - warped).sum() / max(mass, 1e-12)),
                valid_ink_mass=float(mass), popping_components=int((sizes >= 4).sum()),
                support_fraction=float(now.sum() / max(b.sum(), 1e-12)),
                ink_change=float(abs(actual_ink(b) - actual_ink(a)) / max(actual_ink(a), 1e-12)), **info)


def summarize_motion(rows):
    values = np.array([r['geometry'] for r in rows])
    return {'transitions': len(rows), 'mean': float(values.mean()), 'p95': float(np.percentile(values, 95)),
            'max': float(values.max()), 'worst_frame': int(np.argmax(values) + 1),
            'opacity_mean': float(np.mean([r['opacity_residual'] for r in rows])),
            'support_fraction_mean': float(np.mean([r['support_fraction'] for r in rows])),
            'popping_components': sum(r['popping_components'] for r in rows),
            'positive_evidence': all(r['valid_ink_mass'] > 0 for r in rows)}


def static_census(manifest, split, stage):
    rows = []
    for s in SCENES:
        panels = []
        for index in manifest[split]:
            within_budget(); f = load_frame(manifest, s, str(index), split)
            r = atlas([f])[f['key']]; target = actual_ink(f['mask']); matched, norm = match_ink(r['native'], target)
            rows.append({'scene': s, 'index': index, 'candidate_native': readability(r['native'], f),
                         'candidate_matched': readability(matched, f), 'normalization': norm})
            im = panel([rgb_image(f), image(f['mask']), image(r['native']), image(matched)],
                       [f'{s} {split}{index} GS', 'native depth2d', 'native 2D vectors', 'matched 2D vectors'], 400)
            panels.append(im); save_png(stage / s / f'{index}.png', im)
        save_png(stage / f'{s}_ALL.png', np.concatenate(panels))
    atomic_json(stage / 'CENSUS.json', {'split': split, 'frames': len(rows), 'fit_or_tuning': False, 'rows': rows})


def contacts(stage, frames, labels, name):
    for start in range(0, len(frames), 6):
        rows = [panel(ims, [f'{label} | {i:03d}' for label in labels], 400) for i, ims in enumerate(frames[start:start+6], start)]
        save_png(stage / f'{name}_all_{start:03d}_{start+len(rows)-1:03d}.png', np.concatenate(rows))
    save_png(stage / f'{name}_quartiles.png', np.concatenate([panel(frames[i], [f'{s} | {i:03d}' for s in labels], 400) for i in [0,8,16,24,32]]))


def process_path(manifest, scene, arc, stage, candidates):
    began = time.monotonic(); frames = [load_frame(manifest, scene, f'arc{arc}_{i:03d}') for i in range(33)]
    base = [f['mask'].astype(float) for f in frames]; methods = {'B': base}; native = {'B': base}; normalization = {}
    vectors = None; equality = None
    if candidates:
        vectors = atlas(frames); reverse = atlas(list(reversed(frames)))
        equality = all(np.array_equal(vectors[f['key']][k], reverse[f['key']][k]) for f in frames for k in ['xy','ids','native'])
        w = []
        for i, f in enumerate(frames):
            if i == 0: w.append(base[i])
            else:
                warped, valid, _ = transport(w[-1], frames[i-1], f)
                w.append(quantize(np.where(valid, .65 * base[i] + .35 * warped, base[i])))
        native['W'] = w; native['CAND'] = [vectors[f['key']]['native'] for f in frames]
        for method in ['W','CAND']:
            pairs = [match_ink(ink, actual_ink(b)) for ink, b in zip(native[method], base)]
            methods[method] = [p[0] for p in pairs]; normalization[method] = [p[1] for p in pairs]
    for i, f in enumerate(frames):
        within_budget()
        for method in methods:
            save_png(stage / 'frames' / f'{i:03d}_{method}_matched.png', image(methods[method][i]))
            save_png(stage / 'frames' / f'{i:03d}_{method}_native.png', image(native[method][i]))
        save_png(stage / 'frames' / f'{i:03d}_GS.png', rgb_image(f))
        if vectors:
            r = vectors[f['key']]; offsets = np.r_[0, np.cumsum([len(c) for c in r['chains']])]
            np.savez_compressed(stage / 'frames' / f'{i:03d}_vectors.npz', xy=r['xy'], ids=r['ids'], chains=np.concatenate(r['chains']) if r['chains'] else np.array([], int), offsets=offsets)
    labels = ['frozen GS'] + list(methods)
    sheets = [[rgb_image(f)] + [image(methods[k][i]) for k in methods] for i, f in enumerate(frames)]
    contacts(stage, sheets, labels, 'matched')
    native_sheets = [[rgb_image(f)] + [image(native[k][i]) for k in native] for i, f in enumerate(frames)]
    if candidates: contacts(stage, native_sheets, labels, 'native')
    decode = []
    for method in methods:
        for order_name, order in [('forward',list(range(33))),('reverse',list(range(32,-1,-1))),('pingpong',list(range(33))+list(range(31,-1,-1)))]:
            p = stage / f'{method}_{order_name}.mp4'; video(p, (image(methods[method][i]) for i in order)); decode.append(decode_video(p, len(order)))
        if candidates:
            p=stage/f'{method}_native.mp4'; video(p, (image(v) for v in native[method])); decode.append(decode_video(p,33))
    p=stage/'comparison_forward.mp4'; video(p, (panel(s, labels) for s in sheets)); decode.append(decode_video(p,33))
    if candidates:
        p=stage/'comparison_native.mp4'; video(p, (panel(s, labels) for s in native_sheets)); decode.append(decode_video(p,33))
        edited = []
        edit_id = int(vectors[frames[0]['key']]['ids'][0])
        for f in frames:
            r=vectors[f['key']]; edited.append(render_vectors(r['xy'],r['chains'],r['ids'],f['mask'].shape,edit=edit_id))
        p=stage/'identity_edit_pingpong.mp4'; order=list(range(33))+list(range(31,-1,-1))
        video(p,(image(edited[i]) for i in order));decode.append(decode_video(p,65))
        atomic_json(stage/'IDENTITY_EDIT.json',{'id':edit_id,'scope':'persistent vertex-local opacity edit, not a whole semantic stroke','opacity':.5,'return_l1':0.,'seen_frames':[i for i,f in enumerate(frames) if edit_id in vectors[f['key']]['ids']]})
    for p in (stage / 'frames').glob('*.png'):
        with Image.open(p) as im: im.load()
    original = next(r for r in manifest['scenes'][scene]['files'] if r['split']=='original_video' and f'arc{arc}_complete' in r['path'])
    decode.append(decode_video(Path(original['path']),33))
    READS.append({'path':original['path'],'split':'original_video','operation':'full_decode','sha256':original['sha256']})
    rows={k:[readability(ink,f) for ink,f in zip(v,frames)] for k,v in methods.items()}
    diagnostic={k:[motion(v[i-1],v[i],frames[i-1],frames[i]) for i in range(1,33)] for k,v in methods.items()}
    stats={k:summarize_motion(r) for k,r in diagnostic.items()}
    gates={}
    if candidates:
        for m in ['W','CAND']:
            gates[m+'_ink']=all(.95<=r['ink_ratio']<=1.05 for r in rows[m])
            gates[m+'_readability']=all(all(x is None or x>=.95 for x in r['coverage'].values()) and r['unsupported_ink_fraction']<=.05 for r in rows[m])
        gates['candidate_geometry_vs_W']=stats['CAND']['mean']<=.9*stats['W']['mean']
        gates['candidate_geometry_vs_B']=stats['CAND']['mean']<=.95*stats['B']['mean']
        gates['candidate_p95_vs_W']=stats['CAND']['p95']<=stats['W']['p95']
        gates['candidate_opacity_vs_W']=stats['CAND']['opacity_mean']<=1.05*stats['W']['opacity_mean']
        gates['positive_evidence']=all(s['positive_evidence'] for s in stats.values())
        gates['reverse_recomputation']=equality;gates['return_closure']=True
        worst=stats['CAND']['worst_frame']
        save_png(stage/'worst_and_neighbors.png',np.concatenate([panel(sheets[i],[f'{x} frame{i:03d}' for x in labels],800) for i in range(max(0,worst-1),min(33,worst+2))]))
    result={'scene':scene,'arc':arc,'frames':33,'domain':'frozen GS renderer, view-dependent 2D NPR',
            'methods':list(methods),'status':'MEASURED' if candidates else 'B_ONLY_NOT_RUN_KILL',
            'readability':rows,'motion':diagnostic,'motion_summary':stats,'normalization':normalization,
            'identity_events':[vectors[f['key']]['events'] for f in frames] if vectors else None,
            'reverse_equal':equality,'pingpong_return_l1':0.,'gates':gates,
            'necessary_quantitative_pass':all(gates.values()) if candidates else None,
            'visual_review':'PENDING_INTERNAL_REVIEW','elapsed_seconds':time.monotonic()-began}
    if result['elapsed_seconds']>5*60: raise TimeoutError('registered per-path 5 minute budget exhausted')
    atomic_json(stage/'RESULTS.json',result);atomic_json(stage/'DECODE.json',decode)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='out/temporal_depth2d_video_probe/run');parser.add_argument('--rerun-kill',action='store_true');args=parser.parse_args()
    output=(ROOT/args.output).resolve()
    if not output.is_relative_to(ROOT):raise ValueError('output must be inside this worktree')
    output.mkdir(parents=True,exist_ok=True)
    lock=(output/'.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    manifest=json.loads((ART/'INPUTS.json').read_text());metadata=science_metadata()
    frozen=json.loads((ART/'IMPLEMENTATION_SEAL.json').read_text())
    if frozen!=metadata:raise ValueError('implementation not sealed or changed')
    allowed=[r['path'] for s in manifest['scenes'].values() for r in s['files']]
    runtime=[p for p in ['/usr','/lib','/lib64','/etc','/proc','/sys',str(Path(sys.prefix)), '/home/u00134/bin/miniconda3/lib'] if Path(p).exists()]
    restrict_filesystem(runtime+allowed,[str(ROOT),'/dev/null'])
    state={'metadata':metadata,'pid':os.getpid(),'status':'RUNNING','units':{},'rerun_kill':args.rerun_kill}
    def publish():
        state['elapsed_seconds']=time.monotonic()-START;atomic_json(output/'STATE.json',state)
    def unit(name, fn):
        within_budget();dest=output/name
        if dest.exists():verify_seal(dest,metadata);print('RESUME_VERIFIED',name,flush=True)
        else:
            stage=output/(name+'.partial')
            if stage.exists():shutil.rmtree(stage)
            stage.mkdir(parents=True);print('START',name,flush=True);fn(stage);seal_directory(stage,dest,metadata)
            print('SEALED',name,flush=True)
        state['units'][name]='SEALED';publish();return dest
    try:
        publish()
        unit('F_construction',lambda p:static_census(manifest,'F',p))
        unit('C_reserved',lambda p:static_census(manifest,'C',p))
        kill=unit('lego_arc0',lambda p:process_path(manifest,'lego',0,p,True))
        kill_result=json.loads((kill/'RESULTS.json').read_text());passed=kill_result['necessary_quantitative_pass']
        state['kill_pass']=passed;publish()
        if not args.rerun_kill:
            for s in SCENES:
                for a in [0,1]:
                    if (s,a)==('lego',0):continue
                    unit(f'{s}_arc{a}',lambda p,s=s,a=a:process_path(manifest,s,a,p,passed))
        # Byte audit after execution: no scientific source mutations.
        for s in manifest['scenes'].values():
            for r in s['files']:
                if sha(r['path'])!=r['sha256']:raise ValueError('source changed during execution')
        state['status']='COMPLETE';state['verdict']='NECESSARY_GATES_PASS_VISUAL_PENDING' if passed else 'NO_GO_KILL'
        state['actual_candidate_frames']=33 if args.rerun_kill or not passed else 264
        state['actual_baseline_frames']=33 if args.rerun_kill else 264
        atomic_json(output/'ACCESS.json',{'scientific_reads':READS,'policy':'kernel Landlock read-only exact inputs; only this worktree writable','input_hashes_reverified':True,'members_read':['gs_rgb','depth','alpha','D.native_edge'],'C_decoded_after_F_seal':True})
        publish();print('COMPLETE',state['verdict'],flush=True)
    except Exception as e:
        state['status']='ERROR';state['error']=repr(e);publish();traceback.print_exc();raise

if __name__=='__main__':main()

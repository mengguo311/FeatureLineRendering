#!/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
"""Verify sealed stage-1 artifacts without rendering, fitting, or source-image access.

Default native checks read NPY metadata plus original IDs, alpha, and alpha*T.
All other native/typed bytes are checked against the production seal; use
--full-native to additionally decompress every native field for finite checks.
Pixel/source diagnostics are not useful-line scores or independent visual GO.
"""
import argparse
import datetime
import json
import math
from pathlib import Path
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from src.hybrid_raster_io import atomic_json, canonical_hash, hash_file, valid_seal, validate_video
from src.hybrid_raster_stage import F, SCENES, frame_specs, read_inputs, require_evaluation_lock

OUT = ROOT / 'out/hybrid_raster_evidence_v2'
ART = ROOT / 'artifacts/hybrid_raster_evidence_v2'
CHANNELS = ('delta_D', 'delta_A', 'delta_N', 'delta_C', 'delta_G', 'visibility_raw')
A_CHANNELS = ('rgb_fine', 'rgb_coarse', 'alpha', 'depth')
ARMS = ('A', 'B', 'C')
IMAGE_ARMS = (*ARMS, 'A_matched', 'B_matched', 'C_matched', 'author_absolute', 'author_gain')


def ensure(condition, message):
    if not condition: raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text())


def read_npz(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def npz_metadata(path):
    result = {}
    with zipfile.ZipFile(path) as archive:
        ensure(len(archive.namelist()) == len(set(archive.namelist())), 'duplicate NPZ entries')
        for name in archive.namelist():
            ensure(name.endswith('.npy') and '/' not in name, 'unexpected NPZ member path')
            with archive.open(name) as stream:
                version = np.lib.format.read_magic(stream)
                ensure(version in ((1, 0), (2, 0)), 'unsupported NPY header version')
                reader = (np.lib.format.read_array_header_1_0 if version == (1, 0)
                          else np.lib.format.read_array_header_2_0)
                shape, fortran, dtype = reader(stream)
                ensure(not dtype.hasobject, 'object arrays are forbidden')
                result[name[:-4]] = dict(shape=list(shape), dtype=str(dtype), fortran_order=fortran)
    return result


def verify_native(path, shape, count, full_native=False):
    h, w = shape
    expected = dict(rgb=(h,w,3), alpha=(h,w), depth=(h,w), median_depth=(h,w),
                    normal=(h,w,3), radii=(count,), topk_id=(h,w,4), topk_w=(h,w,4),
                    topk_depth=(h,w,4), topk_normal=(h,w,4,3), moment2=(h,w), normal_len=(h,w))
    metadata = npz_metadata(path)
    ensure(set(metadata) == set(expected), 'native field inventory differs')
    for key, dimensions in expected.items():
        ensure(metadata[key]['shape'] == list(dimensions), 'native field dimensions: ' + key)
        ensure(np.issubdtype(np.dtype(metadata[key]['dtype']), np.number), 'nonnumeric native field: ' + key)
    with np.load(path, allow_pickle=False) as data:
        alpha, ids, weights = data['alpha'], data['topk_id'], data['topk_w']
        ensure(np.isfinite(alpha).all() and np.isfinite(weights).all(), 'nonfinite native alpha/weight')
        ensure(ids.dtype.kind in 'iu' and np.all(ids >= -1) and np.all(ids < count), 'invalid original native IDs')
        ensure(np.all(alpha >= 0) and np.all(alpha <= 1 + 3e-6), 'native alpha outside [0,1]')
        ensure(np.all(weights >= 0) and np.all(np.diff(weights, axis=-1) <= 3e-6), 'native contribution ordering')
        ensure(np.all(weights[ids < 0] == 0) and np.all(weights[ids >= 0] > 0), 'empty/contributing ID weight semantics')
        ensure(np.all(ids[alpha == 0] == -1), 'empty native ray retains contributor IDs')
        ensure(np.all(weights.sum(-1) <= alpha + 3e-6), 'raw alpha*T exceeds alpha')
        for i in range(4):
            for j in range(i+1,4):
                ensure(not np.any((ids[...,i] >= 0) & (ids[...,i] == ids[...,j])), 'duplicate original ID in top4')
        if full_native:
            for key in data.files:
                ensure(np.isfinite(data[key]).all(), 'nonfinite native field: ' + key)
        fg = alpha > .05
        mass = weights.sum(-1)
        coverage = mass[fg] / alpha[fg]
    return dict(passed=True, metadata=metadata, original_ids_min=int(ids.min()),
                original_ids_max=int(ids.max()), finite_fields_redecoded=(list(expected) if full_native else ['alpha','topk_w','topk_id']),
                all_native_finite_redecoded=full_native, max_excess_top4_alpha=float((mass-alpha).max()),
                top4_coverage_mean=float(coverage.mean(dtype=np.float64)) if coverage.size else None)


def _check_scalar(value, expected, label):
    if expected is None:
        ensure(value is None, 'diagnostic empty statistic differs: '+label)
    elif isinstance(expected, (int,np.integer)):
        ensure(value == expected, 'diagnostic integer differs: '+label)
    else:
        ensure(isinstance(value,(int,float)) and np.isfinite(value) and
               np.isclose(value,expected,rtol=1e-10,atol=1e-12), 'diagnostic scalar differs: '+label)


def _distribution(value,mask):
    data=np.asarray(value)[mask]
    if data.size==0:
        return dict(count=0,mean=None,min=None,max=None,p05=None,p50=None,p95=None)
    return dict(count=int(data.size),mean=float(data.mean(dtype=np.float64)),min=float(data.min()),max=float(data.max()),
                p05=float(np.percentile(data,5)),p50=float(np.percentile(data,50)),p95=float(np.percentile(data,95)))


def verify_arrays(arrays, provenance, diagnostics, shape, *, native_raw=None):
    """Check cross-artifact equations and provenance; do not rerun evidence extraction."""
    ensure(native_raw is not None, 'native diagnostic buffers required; payload-only checks cannot verify scalar summaries')
    for key in ('alpha','topk_w','normal_len','moment2','depth'):
        expected_shape=(*shape,4) if key=='topk_w' else tuple(shape)
        ensure(key in native_raw and native_raw[key].shape==expected_shape and np.isfinite(native_raw[key]).all(),
               'invalid native diagnostic buffer: '+key)
    for group, values in (('response', arrays), ('provenance', provenance)):
        for key, value in values.items():
            ensure(value.shape == tuple(shape), f'{group} grid mismatch: {key}')
            ensure(np.isfinite(value).all(), f'nonfinite {group}: {key}')
    ensure(diagnostics['shape'] == list(shape), 'diagnostic dimensions differ')
    ensure(diagnostics['B_channel_order'] == list(CHANNELS), 'B source channel order differs')
    ensure(diagnostics['A_channel_order'] == list(A_CHANNELS), 'A source channel order differs')
    for key in IMAGE_ARMS:
        ensure(key in arrays and np.all(arrays[key] >= 0) and np.all(arrays[key] <= 1), 'ink outside [0,1]: ' + key)
    a, b, c = [arrays[key] for key in ARMS]
    fg = provenance['foreground'].astype(bool)
    for key in ARMS:
        ensure(np.all(arrays[key][~fg] == 0), 'ink outside common foreground: ' + key)
    ensure(np.allclose(c, a + b*(1-a), rtol=0, atol=2e-7), 'complement equation differs')
    ensure(np.all(c + 2e-7 >= a) and np.all(c + 2e-7 >= b), 'complement loses source ink')
    expected = dict(A_support=a>0, B_support=b>0, A_only=(a>0)&(b==0),
                    B_only=(b>0)&(a==0), shared=(a>0)&(b>0), overlap=a*b,
                    arm_bits=(a>0).astype(np.uint8) | ((b>0).astype(np.uint8)<<1))
    for key, value in expected.items():
        ensure(np.array_equal(provenance[key], value), 'provenance mismatch: ' + key)
    for arm, channels in (('A', A_CHANNELS), ('B', CHANNELS)):
        stack = np.stack([arrays[f'{arm}_{key}'] for key in channels], axis=-1)
        ensure(np.isfinite(stack).all() and np.all(stack >= 0) and np.all(stack <= 1), 'invalid channel ink')
        ensure(np.array_equal(arrays[arm], stack.max(-1)), 'arm maximum differs from saved channel ink: ' + arm)
        bits = np.zeros(shape, np.uint8)
        for i in range(len(channels)): bits |= (stack[...,i]>0).astype(np.uint8) << i
        ensure(np.array_equal(provenance[arm+'_channel_bits'],bits), 'channel bits differ: ' + arm)
        if arm == 'B':
            dominant = stack.argmax(-1).astype(np.int8); dominant[b==0] = -1
            ensure(np.array_equal(provenance['B_argmax'],dominant), 'B argmax differs')
    mass = {key:float(arrays[key].sum(dtype=np.float64)) for key in ARMS}
    target = min(mass.values())
    matched_mass = {}
    for key in ARMS:
        gain = target/mass[key] if mass[key] else 0.
        matched = arrays[key+'_matched']
        ensure(np.allclose(matched, arrays[key]*gain, rtol=0, atol=2e-7), 'ink matching altered structure/concentration: ' + key)
        matched_mass[key] = float(matched.sum(dtype=np.float64))
        ensure(np.isclose(matched_mass[key], target, rtol=2e-6, atol=1e-4), 'matched opacity mass differs: ' + key)
        stats = diagnostics['arms'][key]
        ensure(np.isclose(stats['mass'],mass[key],rtol=1e-12,atol=1e-7), 'diagnostic opacity mass differs')
        ensure(stats['support'] == int(np.count_nonzero(arrays[key])), 'diagnostic support differs')
        ensure(set(stats['threshold_area'])=={'0.1','0.3','0.5'}, 'diagnostic threshold set differs')
        for threshold in (.1,.3,.5):
            _check_scalar(stats['threshold_area'][str(threshold)],int(np.count_nonzero(arrays[key]>=threshold)),key+'/threshold/'+str(threshold))
        _check_scalar(diagnostics['ink_matching']['gains'][key],gain,'matching/gains/'+key)
        _check_scalar(diagnostics['ink_matching']['original_mass'][key],mass[key],'matching/original_mass/'+key)
    ensure(np.isclose(diagnostics['ink_matching']['target_mass'],target,rtol=1e-12,atol=1e-7), 'diagnostic target mass differs')
    ensure(set(diagnostics['overlap'])=={'A_only','B_only','shared','mass'}, 'diagnostic overlap keys differ')
    for key in ('A_only','B_only','shared'):
        _check_scalar(diagnostics['overlap'][key],int(expected[key].sum()),'overlap/'+key)
    _check_scalar(diagnostics['overlap']['mass'],float((a*b).sum(dtype=np.float64)),'overlap/mass')
    alpha=np.asarray(native_raw['alpha'],np.float32)
    core=alpha>=.5
    outline=ndi.binary_dilation(core,iterations=4)&~ndi.binary_erosion(core,iterations=4,border_value=0)
    strata=dict(background=~(outline|core),outline=outline,interior=core&~outline)
    for arm in ARMS:
        ensure(set(diagnostics['arms'][arm]['strata'])==set(strata), 'diagnostic strata set differs')
        for name,mask in strata.items():
            stored=diagnostics['arms'][arm]['strata'][name]
            _check_scalar(stored['pixels'],int(mask.sum()),arm+'/'+name+'/pixels')
            _check_scalar(stored['mass'],float(arrays[arm][mask].sum(dtype=np.float64)),arm+'/'+name+'/mass')
            _check_scalar(stored['support'],int(np.count_nonzero(arrays[arm][mask])),arm+'/'+name+'/support')
    denom=np.maximum(alpha,1e-8)
    coverage=np.clip(np.asarray(native_raw['topk_w'],np.float32).sum(-1)/denom,0,1).astype(np.float32)
    coherence=np.clip(np.asarray(native_raw['normal_len'])/denom,0,1).astype(np.float32)
    variance=np.maximum(np.asarray(native_raw['moment2'])/denom-np.asarray(native_raw['depth'])**2,0).astype(np.float32)
    raw_statistics={
        'alpha':_distribution(alpha,np.ones(shape,bool)),
        'top4_coverage':_distribution(coverage,alpha>.05),
        'normal_coherence':_distribution(coherence,alpha>.05),
        'depth_variance':_distribution(variance,alpha>.05),
    }
    ensure(set(diagnostics['raw'])==set(raw_statistics),'raw diagnostic field set differs')
    for field,summary in raw_statistics.items():
        ensure(set(diagnostics['raw'][field])==set(summary),'raw statistic keys differ: '+field)
        for statistic,value in summary.items():
            _check_scalar(diagnostics['raw'][field][statistic],value,'raw/'+field+'/'+statistic)
    channel_counts = {}
    b_only = provenance['B_only']
    for index, name in enumerate(CHANNELS):
        support = (provenance['B_channel_bits'] & (1<<index)) != 0
        dominant = provenance['B_argmax'] == index
        channel_counts[name] = dict(support_pixels=int(support.sum()), dominant_pixels=int(dominant.sum()),
                                   B_only_support_pixels=int((support & b_only).sum()),
                                   B_only_dominant_pixels=int((dominant & b_only).sum()),
                                   ink_mass=float(arrays['B_'+name].sum(dtype=np.float64)))
    return dict(passed=True, shape=list(shape), mass=mass, matched_mass=matched_mass,
                support={key:int(np.count_nonzero(arrays[key])) for key in ARMS},
                overlap_pixels={key:int(provenance[key].sum()) for key in ('A_only','B_only','shared')},
                B_source_diagnostics=channel_counts,
                native_raw_statistics_checked=raw_statistics,
                scalar_diagnostics_checked=['arm mass/support/threshold areas','overlap count/mass','matching target/gains/original mass','native-alpha strata pixels/mass/support','raw distribution count/mean/min/max/p05/p50/p95'],
                qualification='Support and argmax distributions describe saved responses, not physical line truth or visual quality.')


def expected_context(spec, checkpoint, lock, raw_only=False):
    config = lock['config']
    context = dict(scene=spec['scene'], key=spec['key'], camera=spec['camera'],
                   camera_hash=canonical_hash(spec['camera']), checkpoint_sha256=checkpoint['sha256'],
                   renderer_source_sha256=config['sources']['src/hybrid_raster_native.py'],
                   calibration_sha256=config['calibration_sha256'],
                   render_recipe={'SH':0,'topk':4,'background':'white','kernel_size':0})
    if not raw_only:
        context.update(parameter_hash=lock['parameter_hash'],source_hashes=config['sources'])
    return context


def png_size(path, expected):
    with Image.open(path) as im:
        ensure(im.format == 'PNG' and im.mode == 'RGB' and im.size == tuple(expected), 'PNG native dimensions/mode differ: ' + str(path))


def verify_frame(spec, inputs, lock, full_native=False):
    scene, key = spec['scene'], spec['key']
    frame = OUT/'frames'/scene/key
    checkpoint = inputs['scenes'][scene]['checkpoint']
    context = expected_context(spec, checkpoint, lock)
    ensure(valid_seal(frame,context), 'frame does not exist: ' + str(frame))
    seal = read_json(frame/'SEAL.json')
    ensure(read_json(frame/'camera.json') == context, 'sealed camera metadata differs')
    required = {'native.npz','typed.npz','responses.npz','provenance.npz','camera.json','diagnostics.json','rgb.png',
                'line_panel.png','overlay_panel.png','matched_panel.png','response_panel.png'}
    required.update(f'{arm}_{kind}.png' for arm in IMAGE_ARMS for kind in ('ink','overlay'))
    ensure(set(seal['files']) == required, 'frame artifact inventory incomplete/unexpected')
    raw = OUT/'raw'/scene/key
    raw_seal = read_json(raw/'SEAL.json')
    ensure(hash_file(raw/'SEAL.json') == (raw/'SEAL.sha256').read_text().strip(), 'raw seal digest differs')
    raw_context = expected_context(spec,checkpoint,lock,raw_only=True)
    ensure(raw_seal['context'] == raw_context and raw_seal['context_sha256'] == canonical_hash(raw_context), 'raw source/camera context differs')
    ensure(set(raw_seal['files']) == {'native.npz','camera.json','checkpoint_qualification.json'}, 'raw seal inventory differs')
    for name, digest in raw_seal['files'].items():
        # Native bytes were already checked in the frame seal. Both paths must
        # still refer to the same hardlink to avoid hashing the large file twice.
        if name == 'native.npz':
            ensure((raw/name).samefile(frame/name) and seal['files'][name] == digest, 'raw/frame native buffer differs')
        else: ensure(hash_file(raw/name) == digest, 'raw metadata digest differs: ' + name)
    qualification = read_json(raw/'checkpoint_qualification.json')
    ensure(qualification['sha256'] == checkpoint['sha256'], 'checkpoint qualification source differs')
    ensure(qualification['proxy_axis_normals_computed'] is False, 'proxy surface normals entered method')
    ensure(qualification['filter_3D_applied'] is False, 'unexpected filter_3D application')
    h,w = spec['camera']['native_height'],spec['camera']['native_width']
    native = verify_native(frame/'native.npz',(h,w),qualification['gaussians'],full_native)
    typed = npz_metadata(frame/'typed.npz')
    for field in ('q_s','q','u','ell','E_V','delta_A','delta_D','delta_N','delta_C','delta_G','E_A','E_D','E_N','E_C','E_G','L','S_L','E_T','visibility_raw','topk_mass','normal_coherence','depth_variance'):
        ensure(typed.get(field,{}).get('shape') == [h,w], 'missing/wrong typed field: '+field)
    ensure(typed.get('normalized_topk_w',{}).get('shape') == [h,w,4], 'normalized top4 metadata differs')
    ensure(typed.get('visible_color',{}).get('shape') == [h,w,3], 'visible color metadata differs')
    arrays, provenance = read_npz(frame/'responses.npz'),read_npz(frame/'provenance.npz')
    diagnostics = read_json(frame/'diagnostics.json')
    ensure(diagnostics['parameter_hash'] == lock['parameter_hash'] and diagnostics['camera_hash'] == context['camera_hash'], 'diagnostic configuration differs')
    ensure(diagnostics['native_sha256'] == seal['files']['native.npz'], 'diagnostic native buffer differs')
    with np.load(frame/'native.npz',allow_pickle=False) as data:
        diagnostic_native={key:data[key] for key in ('alpha','topk_w','normal_len','moment2','depth')}
    response = verify_arrays(arrays,provenance,diagnostics,(h,w),native_raw=diagnostic_native)
    foreground = cv2.dilate((diagnostic_native['alpha']>=.08).astype(np.uint8),np.ones((3,3),np.uint8))>0
    ensure(np.array_equal(foreground,provenance['foreground']), 'common foreground differs from native alpha')
    with np.load(frame/'typed.npz',allow_pickle=False) as data:
        original = data['S_L']
    ensure(np.array_equal(original,arrays['author_absolute']), 'author original formula output altered')
    ensure(np.allclose(arrays['author_gain'],np.clip(original/lock['normalization']['author_scale'],0,1),rtol=0,atol=2e-7), 'author F-only display gain differs')
    for name in required:
        if name.endswith('.png'):
            dimensions = (w,h)
            if name == 'line_panel.png': dimensions=(5*w,h+32)
            elif name in ('overlay_panel.png','matched_panel.png'): dimensions=(3*w,h+32)
            elif name == 'response_panel.png': dimensions=(5*w,3*(h+32))
            png_size(frame/name,dimensions)
    return dict(scene=scene,key=key,split=spec['split'],passed=True,seal_sha256=hash_file(frame/'SEAL.json'),
                camera_hash=context['camera_hash'],native=native,responses=response,
                checkpoint_qualification=qualification,diagnostics=diagnostics,files=seal['files'],
                raw_seal_sha256=hash_file(raw/'SEAL.json'),raw_files=raw_seal['files'])


def verify_media(scene, specs, records, lock):
    dest = OUT/'media'/scene
    context = dict(scene=scene,parameter_hash=lock['parameter_hash'],
                   frames=[dict(key=s['key'],seal_sha256=records[s['key']]['seal_sha256']) for s in specs],
                   fps=12,arc_frames=33,native_full_resolution_tiles=True)
    ensure(valid_seal(dest,context), 'scene media missing: '+scene)
    seal = read_json(dest/'SEAL.json'); manifest = read_json(dest/'MANIFEST.json')
    ensure(manifest['scene']==scene and manifest['parameter_hash']==lock['parameter_hash'], 'media manifest context differs')
    ensure(set(manifest['videos'])=={'comparison','overlay','matched'}, 'media video set differs')
    h,w=specs[0]['camera']['native_height'],specs[0]['camera']['native_width']
    videos={}
    for name,columns in (('comparison',5),('overlay',3),('matched',3)):
        path=dest/f'arc0_{name}.mp4'
        value=validate_video(path,expected_frames=33,expected_size=(columns*w,h+32))
        old=manifest['videos'][name]
        for key in ('frames','distinct_frames','size','frame_sha256','sha256'):
            ensure(value[key]==old[key], 'video differs from sealed decode manifest: '+name+'/'+key)
        ensure(old['fps']==12 and Path(old['path'])==path, 'video path/fps differs')
        videos[name]=value
    contacts={}
    expected_contacts={f'{split}_{arm}_contact.png' for split in ('F','C','arc0') for arm in ('rgb','A','B','C','author_gain')}
    ensure(set(manifest['contacts'])==expected_contacts, 'full-frame contact inventory differs')
    for name in sorted(expected_contacts):
        split=name.split('_',1)[0]; columns=3 if split=='arc0' else 4; count=33 if split=='arc0' else 8
        dimensions=(columns*w,math.ceil(count/columns)*(h+32)); png_size(dest/name,dimensions)
        ensure(manifest['contacts'][name]['sha256']==seal['files'][name], 'contact checksum differs')
        contacts[name]=dict(size=list(dimensions),sha256=seal['files'][name])
    representatives=[]
    for index in (0,16,32):
        for kind,columns in (('line',5),('overlay',3),('matched',3)):
            name=f'arc0_{index:03d}_{kind}.png'; png_size(dest/name,(columns*w,h+32))
            ensure(seal['files'][name]==records[f'arc0_{index:03d}']['files'][f'{kind}_panel.png'], 'representative frame differs')
            representatives.append(name)
    ensure(set(seal['files'])==expected_contacts | {'MANIFEST.json'} | {f'arc0_{name}.mp4' for name in videos} | set(representatives), 'media seal inventory differs')
    return dict(passed=True,seal_sha256=hash_file(dest/'SEAL.json'),videos=videos,contacts=contacts,files=seal['files'])


def verify_sources(lock, inputs):
    config=lock['config']
    ensure(hash_file(ART/'PROTOCOL.md')==config['protocol_sha256'], 'protocol changed after F lock')
    ensure(hash_file(ROOT/'artifacts/direct_curve_global_fit_probe/INPUTS.json')==config['input_manifest_sha256'], 'input manifest changed')
    for name,digest in config['sources'].items(): ensure(hash_file(ROOT/name)==digest, 'frozen source changed: '+name)
    calibration_path=OUT/'calibration/CALIBRATION.json'
    ensure(hash_file(calibration_path)==config['calibration_sha256'], 'calibration report changed')
    calibration=read_json(calibration_path)
    ensure(calibration['status']=='PASS' and calibration['source']==config['native_build'], 'current source was not calibrated')
    build=config['native_build']
    ensure(read_json(OUT/'native/BUILD.json')['build_hash']==build['build_hash'], 'native build manifest changed')
    ensure(hash_file(OUT/'native/SOURCE_MANIFEST.json')==build['source_manifest_sha256'], 'native source manifest changed')
    for variant in build['variants'].values(): ensure(hash_file(variant['path'])==variant['sha256'], 'native compiled binary changed')
    ensure(read_json(OUT/'CONFIG.json')==config, 'standalone CONFIG differs from lock')
    normalization=read_json(OUT/'NORMALIZATION.json')
    ensure(normalization['normalization']==lock['normalization'] and normalization['F_native_sources']==lock['F_native_sources'], 'F normalization record differs')
    ensure(lock['normalization']['frame_count']==16, 'normalization was not fit on exact primary F count')
    expected={(s,f'F_{i:03d}') for s in ('lego','chair') for i in F}
    ensure({(r['scene'],r['key']) for r in lock['F_native_sources']}==expected, 'normalization includes wrong frame domain')
    ensure(len(lock['F_native_sources'])==16, 'duplicate normalization source frames')
    for record in lock['F_native_sources']:
        camera=inputs['scenes'][record['scene']]['cameras'][str(int(record['key'].split('_')[1]))]
        seal=read_json(OUT/'frames'/record['scene']/record['key']/'SEAL.json')
        ensure(record['camera_hash']==canonical_hash(camera), 'F normalization camera differs')
        ensure(record['native_sha256']==seal['files']['native.npz'], 'F normalization used another native buffer')
    ensure({(r['scene'],r['index']) for r in calibration['frames']}=={(s,i) for s in ('lego','chair') for i in (1,41)}, 'calibration did not cover exact engineering slice')
    return dict(passed=True,parameter_hash=lock['parameter_hash'],native_build=build,
                calibration_sha256=config['calibration_sha256'],source_files=config['sources'])


def run(scenes, output, full_native=False):
    started=time.monotonic(); inputs=read_inputs()
    report=dict(schema='hybrid-raster-verification-v1',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                scenes=list(scenes),full_native=full_native,frames={},media={},missing=[],errors=[],passed=False,
                source_image_access='NONE; only INPUTS metadata and this stage sealed rendered outputs',
                finite_check_scope=('all native fields redecoded' if full_native else 'native alpha/IDs/alpha*T plus depth/moment2/normal_len diagnostic buffers redecoded; other native/typed bytes hash-checked against producer-validation seals'),
                scientific_qualification='Engineering/artifact integrity and pixel diagnostics only; no useful-line metric, scientific GO, or independent human review.')
    if not (OUT/'LOCK.json').is_file():
        report['missing'].append('LOCK.json: primary F is not yet sealed')
        lock=None
    else:
        try:
            lock=require_evaluation_lock(OUT)
            report['sources']=verify_sources(lock,inputs)
        except Exception as error:
            report['errors'].append(dict(where='global_lock_sources',error=f'{type(error).__name__}: {error}')); lock=None
    for scene in scenes:
        specs=[s for split in ('F','C','arc0') for s in frame_specs(inputs,scene,split)]
        records={}; report['frames'][scene]=records
        if lock is not None:
            checkpoint=inputs['scenes'][scene]['checkpoint']
            try: ensure(hash_file(checkpoint['path'])==checkpoint['sha256'], 'frozen checkpoint changed')
            except Exception as error: report['errors'].append(dict(where=scene+'/checkpoint',error=str(error))); continue
        for spec in specs:
            path=OUT/'frames'/scene/spec['key']
            if not path.exists(): report['missing'].append(scene+'/'+spec['key']); continue
            if lock is None: continue
            try:
                records[spec['key']]=verify_frame(spec,inputs,lock,full_native)
                print(f"VERIFIED {scene} {spec['key']}",flush=True)
            except Exception as error:
                report['errors'].append(dict(where=scene+'/'+spec['key'],error=f'{type(error).__name__}: {error}'))
        if not (OUT/'media'/scene).exists(): report['missing'].append(scene+'/media')
        elif lock is not None and len(records)==49:
            try: report['media'][scene]=verify_media(scene,specs,records,lock)
            except Exception as error: report['errors'].append(dict(where=scene+'/media',error=f'{type(error).__name__}: {error}'))
    report['counts']=dict(expected_frames=49*len(scenes),verified_frames=sum(len(r) for r in report['frames'].values()),
                          expected_media_scenes=len(scenes),verified_media_scenes=len(report['media']))
    report['passed']=not report['missing'] and not report['errors'] and report['counts']['verified_frames']==49*len(scenes) and len(report['media'])==len(scenes)
    report['status']='PASS' if report['passed'] else ('INVALID' if report['errors'] else 'INCOMPLETE')
    report['elapsed_seconds']=time.monotonic()-started
    report['verifier_sha256']=hash_file(__file__)
    atomic_json(output,report,replace=True)
    print(json.dumps({k:report[k] for k in ('status','counts','missing','errors')},ensure_ascii=False),flush=True)
    return 0 if report['passed'] else (1 if report['errors'] else 2)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenes',nargs='+',choices=SCENES,default=list(SCENES))
    parser.add_argument('--output',type=Path,default=ART/'VERIFICATION.json')
    parser.add_argument('--full-native',action='store_true')
    args=parser.parse_args()
    ensure(len(args.scenes)==len(set(args.scenes)), 'duplicate scenes requested')
    ensure(ROOT in args.output.resolve().parents, 'verification output must remain in authorized worktree')
    return run(args.scenes,args.output,args.full_native)


if __name__=='__main__': raise SystemExit(main())

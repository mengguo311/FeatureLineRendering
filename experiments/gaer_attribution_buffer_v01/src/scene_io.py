"""Read original trained PLY rows and frozen cameras without importing old runtimes."""
import json
import math
from pathlib import Path
import re
import numpy as np
import torch
from plyfile import PlyData
from PIL import Image
from runtime import ART, DATA_FREEZE, atomic_json, digest, sha

def freeze_cameras():
    data = json.loads(DATA_FREEZE.read_text())
    records = {}
    for name in ('lego', 'chair'):
        scene = data['scenes'][name]
        model = Path(scene['model'])
        if sha(model) != scene['model_sha256']:
            raise RuntimeError('frozen checkpoint mismatch: ' + name)
        input_path = Path(re.search("source_path='([^']+)'", scene['cfg_args'])[1])
        meta_path = input_path / 'transforms_train.json'
        metadata = json.loads(meta_path.read_text())
        entries = {e['index']: e for values in scene['roles'].values() for e in values}
        cameras = []
        for index in (1, 14):
            entry = entries[index]
            matches = [(j, f) for j, f in enumerate(metadata['frames'])
                       if Path(f['file_path']).stem == Path(entry['original_path']).stem]
            if len(matches) != 1:
                raise RuntimeError('camera filename must match exactly one actual metadata frame')
            metadata_index, frame = matches[0]
            c2w = np.asarray(frame['transform_matrix'], dtype=np.float64).copy()
            c2w[:3, 1:3] *= -1  # Actual Blender dataset convention, as stock loader.
            w2c = np.linalg.inv(c2w)
            error = float(np.max(np.abs(w2c - np.asarray(entry['camera']['w2c']))))
            if error > 1e-10:
                raise RuntimeError('actual metadata and frozen camera differ')
            original_image = Path(entry['original_path'])
            with Image.open(original_image) as im:
                width, height = im.size
            if (width, height) != (800, 800):
                raise RuntimeError('actual camera is not native 800x800')
            fovx = float(metadata['camera_angle_x'])
            focal = width / (2 * math.tan(fovx / 2))
            fovy = 2 * math.atan(height / (2 * focal))
            if abs(fovx - entry['camera']['FoVx']) > 1e-10:
                raise RuntimeError('actual FoV differs from freeze')
            camera = dict(index=index, metadata_index=metadata_index, frame_file=frame['file_path'], width=width, height=height,
                          FoVx=fovx, FoVy=fovy, w2c=w2c.tolist(),
                          K=[[focal, 0, (width-1)/2], [0, focal, (height-1)/2], [0, 0, 1]],
                          metadata_path=str(meta_path), metadata_sha256=sha(meta_path),
                          original_image=str(original_image), original_image_sha256=sha(original_image),
                          frozen_camera_hash_512=entry['camera_hash'], metadata_w2c_max_error=error)
            camera['camera_sha256'] = digest(camera)
            cameras.append(camera)
        records[name] = dict(model=str(model), model_sha256=sha(model), count=scene['ply']['count'],
                             sh_degree=3, training_iteration=30000, cameras=cameras,
                             training_manifest=scene['training_manifest'],
                             training_manifest_sha256=sha(scene['training_manifest']))
    result = dict(data_freeze_path=str(DATA_FREEZE), data_freeze_sha256=sha(DATA_FREEZE), scenes=records)
    atomic_json(ART / 'CAMERA_FREEZE.json', result)
    return result

def load_model(record):
    path = Path(record['model'])
    if sha(path) != record['model_sha256']:
        raise RuntimeError('checkpoint changed')
    v = PlyData.read(str(path))['vertex']
    def stack(names):
        return np.stack([v[n] for n in names], axis=1).astype(np.float32)
    xyz = stack(['x', 'y', 'z'])
    dc = stack(['f_dc_' + str(i) for i in range(3)])[:, None, :]
    rest_names = sorted([p.name for p in v.properties if p.name.startswith('f_rest_')], key=lambda x: int(x.split('_')[-1]))
    if len(rest_names) != 45 or len(xyz) != record['count']:
        raise RuntimeError('requires all original rows and full SH3')
    rest = stack(rest_names).reshape(len(xyz), 3, 15).transpose(0, 2, 1)
    def gpu(a):
        return torch.tensor(a, dtype=torch.float32, device='cuda').contiguous()
    # Exactly the stock GaussianModel PLY order/activations; original row IDs retained.
    return dict(means3D=gpu(xyz), means2D=torch.zeros_like(gpu(xyz)),
                shs=gpu(np.concatenate([dc, rest], axis=1)),
                opacities=torch.sigmoid(gpu(stack(['opacity']))),
                scales=torch.exp(gpu(stack(['scale_' + str(i) for i in range(3)]))),
                rotations=torch.nn.functional.normalize(gpu(stack(['rot_' + str(i) for i in range(4)])), dim=1))

def make_settings(module, camera):
    view = torch.tensor(np.asarray(camera['w2c']).T, dtype=torch.float32, device='cuda')
    tx, ty = math.tan(camera['FoVx']/2), math.tan(camera['FoVy']/2)
    near, far = .01, 100.
    # Stock utils.graphics_utils.getProjectionMatrix arithmetic/FP32 assignments.
    p = torch.zeros(4, 4)
    right, left, top, bottom = tx*near, -tx*near, ty*near, -ty*near
    p[0,0] = 2*near/(right-left); p[1,1] = 2*near/(top-bottom)
    p[0,2] = (right+left)/(right-left); p[1,2] = (top+bottom)/(top-bottom)
    p[3,2] = 1.; p[2,2] = far/(far-near); p[2,3] = -(far*near)/(far-near)
    p = p.T.cuda()
    return module.GaussianRasterizationSettings(camera['height'], camera['width'], tx, ty,
        torch.ones(3, device='cuda'), 1., view, view @ p, 3, view.inverse()[3,:3], False, False)

"""Complete owned-run checkpoints; no compatibility claim with upstream tuples."""
import json
import os
from pathlib import Path
import random
import uuid

import numpy as np
import torch
from safety import atomic_json, sha256

PARAMETERS = ('_xyz','_features_dc','_features_rest','_scaling','_rotation',
              '_opacity','_appearance_embeddings')
BUFFERS = ('max_radii2D','min_radii2D','xyz_gradient_accum','xyz_gradient_accum_abs',
           'xyz_gradient_accum_abs_max','denom','filter_3D')


def save_checkpoint(path, model, completed_iteration, camera_stack, provenance, cuda=True):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    payload = {'schema':1, 'provenance':provenance, 'completed_iteration':completed_iteration,
               'camera_stack':camera_stack, 'parameters':{k:getattr(model,k).detach() for k in PARAMETERS},
               'buffers':{k:getattr(model,k) for k in BUFFERS},
               'active_sh_degree':model.active_sh_degree, 'spatial_lr_scale':model.spatial_lr_scale,
               'appearance_network':model.appearance_network.state_dict(),
               'optimizer':model.optimizer.state_dict(),
               'rng_python':random.getstate(),'rng_numpy':np.random.get_state(),
               'rng_torch':torch.get_rng_state(),
               'rng_cuda':torch.cuda.get_rng_state_all() if cuda else None}
    # Immutable generations + atomic pointer: a power failure never pairs a new
    # checkpoint with an old checksum. Keep the preceding verified generation.
    generation = path.with_name(path.name+'.generation-'+uuid.uuid4().hex)
    with open(generation,'xb') as f:
        torch.save(payload,f)
        f.flush();os.fsync(f.fileno())
    descriptor = {'schema':1,'path':str(generation.resolve()),'sha256':sha256(generation),
                  'completed_iteration':completed_iteration,'provenance':provenance}
    old = json.loads(path.read_text()) if path.exists() else None
    atomic_json(path,descriptor)
    if old:
        atomic_json(path.with_name(path.name+'.previous.json'),old)
    # Only delete older generations owned by this exact checkpoint basename.
    keep = {generation.resolve(), Path(old['path']).resolve() if old else generation.resolve()}
    for item in path.parent.glob(path.name+'.generation-*'):
        if item.resolve() not in keep:
            item.unlink()
    return descriptor


def checkpoint_descriptor(path, provenance):
    try:
        desc = json.loads(Path(path).read_text())
        if desc['schema'] != 1 or desc['provenance'] != provenance or sha256(desc['path']) != desc['sha256']:
            raise ValueError('checkpoint provenance/hash mismatch')
        return desc
    except (OSError,KeyError,TypeError,json.JSONDecodeError) as exc:
        raise ValueError('unverified checkpoint') from exc


def restore_checkpoint(path, model, options, provenance, cuda=True):
    desc = checkpoint_descriptor(path,provenance)
    # Only our own hash-verified checkpoint is loaded (torch pickle format).
    device = model._xyz.device
    state = torch.load(desc['path'],map_location=device)
    if state['schema'] != 1 or state['provenance'] != provenance:
        raise ValueError('payload provenance mismatch')
    for key in PARAMETERS:
        setattr(model,key,torch.nn.Parameter(state['parameters'][key].to(device)))
    model.active_sh_degree = state['active_sh_degree']
    model.spatial_lr_scale = state['spatial_lr_scale']
    model.appearance_network.load_state_dict(state['appearance_network'])
    model.training_setup(options)
    for key in BUFFERS:
        setattr(model,key,state['buffers'][key].to(device))
    model.optimizer.load_state_dict(state['optimizer'])
    random.setstate(state['rng_python']);np.random.set_state(state['rng_numpy'])
    torch.set_rng_state(state['rng_torch'].cpu())
    if cuda:
        torch.cuda.set_rng_state_all([x.cpu() for x in state['rng_cuda']])
    return state['completed_iteration'],state['camera_stack']

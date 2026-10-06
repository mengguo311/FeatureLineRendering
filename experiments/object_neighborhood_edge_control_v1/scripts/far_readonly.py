"""Independent B0/C0 observation after frozen C1 certificate failure.

No optimizer, C1 fallback, relaxed threshold, or TEST access. This does not seal
the failed selection unit or claim a completed far-scene control experiment.
"""
import json
import shutil
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from runtime import EXP, OUT, atomic_json, sha
from runner import unit

def collect():
    import numpy as np
    from adjacency import center_pairs
    scene = 'far_background'; directory = OUT / 'controls' / scene
    cfg = json.loads((EXP / 'configs/pilot.json').read_text())
    identity = json.loads((directory / 'identity.json').read_text())
    mu = np.asarray(identity['anchor']); labels = np.asarray(identity['label']); uids = np.asarray(identity['uid'])
    with np.load(directory / 'fixed_labels.npz') as values:
        mass = values['band_mass'].copy(); total = values['total_mass'].copy()
    start = time.monotonic()
    pairs = center_pairs(mu, labels, cfg['selection']['center_radius'])
    duration = time.monotonic() - start
    candidates = sorted(set(i for pair in pairs for i in pair)); visible = mass > cfg['selection']['band_mass_min']
    selected = [i for i in candidates if visible[i]]
    initial = OUT / f'models/{scene}/chkpnt7000.pth'; b0 = directory / 'B0.pth'
    if b0.exists():
        assert sha(b0) == sha(initial)
    else:
        shutil.copyfile(initial, b0)
    result = {'scene': scene, 'N': len(labels), 'decision': 'C1_ENGINEERING_REFUSAL_NO_CONTROL_EXECUTED',
        'oracle_surface_used': False, 'label_counts': {str(k): int((labels == k).sum()) for k in (-1, 0, 1, 2)},
        'C0_time_seconds': duration, 'C1_time_seconds': None, 'C1_distance_certificate_count': None,
        'C1_uncertified_decisions': None, 'selections': {'C0': {'candidate_count': len(selected),
            'relation': 'Gaussian_neighborhood_proxy_not_contact', 'visible_contribution_recall': float(mass[selected].sum()/max(mass.sum(), 1e-8))}},
        'C0_pairs': len(pairs), 'C0_uid_sha256': None,
        'threshold': cfg['selection']['center_radius'], 'fixed_labels_sha256': sha(directory/'fixed_labels.npz'),
        'identity_sha256': sha(directory/'identity.json'), 'initial_checkpoint_sha256': sha(initial),
        'purpose': 'read-only partial C0 diagnostics; does not complete or bypass failed C1 selection'}
    uidfile=directory/'C0_observation_uids.json'; atomic_json(uidfile, {'uids': uids[selected].tolist()})
    result['C0_uid_sha256']=sha(uidfile)
    atomic_json(EXP/f'results/manifests/selection_{scene}_partial.json', result)
    atomic_json(EXP/f'results/manifests/{scene}_B0_edit.json', {'scene': scene, 'method': 'B0', 'no_op': True,
        'initial_sha256': sha(initial), 'output_sha256': sha(b0), 'iterations': 0,
        'changed_rows': {'_xyz': 0, '_features_dc': 0, '_scaling': 0, '_rotation': 0, '_opacity': 0},
        'selection_not_required': 'B0 existing naturally trained model, exact file copy, no editing'})
    log=OUT/'logs/select_far_background.txt'
    atomic_json(EXP/'results/manifests/far_C1_failure.json', {'status': 'ENGINEERING_NOT_READY',
        'error': 'uncertified ellipsoid distance interval [0.019994966764112082,0.02001964881959949]',
        'frozen_threshold': .02, 'last_completed_chunks': 7, 'total_chunks': 66,
        'last_certified_neighbors_reported': 30554, 'full_pair_count': None, 'full_duration_seconds': None,
        'log_sha256': sha(log), 'no_threshold_or_source_change': True, 'C1_control': None,
        'resume_policy': 'same configuration may reproduce refusal; do not bypass certificate or retune current frozen method'})
    # Oracle physical relation is separately labeled evaluator-only evidence.
    mesh=OUT/f'data/{scene}/oracle_eval/mesh_GT.npz'
    with np.load(mesh) as gt: distance=float(gt['contact_distance'])
    atomic_json(EXP/'results/tables/far_spatial_oracle_evaluation.json', {'scope': 'new synthetic GT evaluation only',
        'source_sha256': sha(mesh), 'minimum_surface_distance_world': distance,
        'physical_relation': 'separated_far_background', 'main_input': False,
        'C0_proxy_has_candidates': bool(selected), 'proxy_is_surface_contact': False, 'C1_evaluation': None})

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--collect':
        collect()
    else:
        script=EXP/'scripts/far_readonly.py'
        unit('far_readonly_observation',[str(script),'--collect'],
            [OUT/'controls/far_background/B0.pth', EXP/'results/manifests/selection_far_background_partial.json'])
        unit('far_B0_val_after_C1_refusal',[str(EXP/'scripts/evaluate.py'),'far_background','B0'],
            [EXP/'results/tables/far_background_B0_val.json'])

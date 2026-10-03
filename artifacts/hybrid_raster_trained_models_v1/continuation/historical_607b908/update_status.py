"""Read-only training observer; atomically update the task's progress summary."""
import datetime
import json
from pathlib import Path
import os
import shutil

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'artifacts/hybrid_raster_trained_models_v1'
OUT = ROOT / 'out/hybrid_raster_trained_models_v1'
SCENES = ['hotdog', 'materials', 'mic', 'ship']


def main():
    path = ART / 'STATUS.json'
    value = json.loads(path.read_text()) if path.exists() else {}
    rows = {}
    for scene in SCENES:
        status = OUT / f'training/{scene}/seed_1729/STATUS.json'
        rows[scene] = json.loads(status.read_text()) if status.exists() else {'state': 'NOT_LAUNCHED', 'iteration': 0}
    value['training'] = rows
    value['updated_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    value['storage_free_bytes'] = shutil.disk_usage(OUT).free
    value['completed_acquisitions'] = sum(x['state'] == 'COMPLETE' for x in rows.values())
    value['expected_scenes'] = 4
    value['expected_npr_frames'] = 196
    value['actual_npr_frames'] = len(list((OUT / 'transport/frames').glob('*/*/SEAL.json')))
    if not value.get('phase', '').startswith('NPR_'):
        if any(x['state'] in ('STARTING', 'TRAINING') for x in rows.values()):
            value['phase'] = 'ACQUIRING_VANILLA_TRAIN_ONLY'
        elif value['completed_acquisitions'] == 4:
            value['phase'] = 'ACQUIRED_WAITING_CHECKPOINT_AND_CAMERA_FREEZE'
        elif any(x['state'] == 'FAILED' for x in rows.values()):
            value['phase'] = 'ACQUISITION_PARTIAL_OR_FAILED'
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)
    print(json.dumps({'phase': value['phase'], 'scenes': {s: {'state': r['state'], 'iteration': r.get('iteration')} for s, r in rows.items()}, 'free_bytes': value['storage_free_bytes']}))


if __name__ == '__main__':
    main()

"""Only an explicit, resolved DTU half30k entry of the frozen paper protocol."""
import json
from pathlib import Path
from safety import sha256
HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
PROTOCOL_SHA='f2b623124d648180ed31704f0070f50248fab945a84a92d0232fd69958784aba'

def validate_config_scope(c):
    try:
        if c['dataset']!='DTU' or c['automatic_scene_limit']!=1 or c['iterations']!=30000 or c['resolution_divisor']!=2:
            raise ValueError('only one resolved DTU half30k entry allowed')
        p=Path(c['full_suite_protocol'])
        if c['full_suite_protocol_sha256']!=PROTOCOL_SHA or sha256(p)!=PROTOCOL_SHA:raise ValueError('frozen full-suite protocol mismatch')
        entry=next(e for e in json.loads(p.read_text())['entries'] if e['id']==c['entry_id'])
        if not (entry['id']==f"DTU_{c['scene']}_half30k_TSDF" and entry['dataset']=='DTU' and entry['scene']==c['scene'] and entry['iterations']==30000 and entry['resolution_divisor']==2 and not entry['unresolved'] and entry['schedule']=={'photo':[1,15000],'geometry':[15001,30000]}):
            raise ValueError('unresolved or mismatching scientific entry')
        if Path(c['data']).resolve()!=HDD/'data/prepared'/c['scene']:raise ValueError('prepared data/scene mismatch')
        if not Path(c['model']).resolve().is_relative_to(HDD/'models'):raise ValueError('isolated model path required')
        return entry
    except (KeyError,StopIteration,TypeError,OSError) as exc:
        raise ValueError('incomplete scientific scope') from exc

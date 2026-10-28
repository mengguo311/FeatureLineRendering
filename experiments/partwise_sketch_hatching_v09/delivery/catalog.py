"""File integrity only: no numerical or renderer imports."""
import runtime
from pathlib import Path

def file_record(path, group):
    p = Path(path).resolve()
    return dict(path=str(p), group=group, size=p.stat().st_size, sha256=runtime.sha(p))

def check_records(records):
    errors = []
    for r in records:
        p = Path(r['path'])
        if not p.is_file():
            errors.append(dict(path=str(p), kind='missing'))
        elif p.stat().st_size != r['size'] or runtime.sha(p) != r['sha256']:
            errors.append(dict(path=str(p), kind='mismatch'))
    return errors

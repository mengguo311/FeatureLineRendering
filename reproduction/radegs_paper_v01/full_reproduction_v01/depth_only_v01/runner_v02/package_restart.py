"""Preserve interrupted delivery evidence before a single supervised retry."""
from pathlib import Path
import time

def preserve_incomplete(path):
 path=Path(path)
 if not path.exists():return None
 target=path.with_name(path.name+'.incomplete-'+str(time.time_ns()))
 if target.exists():raise FileExistsError(target)
 path.rename(target)
 return target

"""Explicit bootstrap accounting over kernel-level file-open traces."""
from pathlib import Path
import importlib.util
import marshal
import struct
from .foundation import audit_opens


def bytecode_matches_source(cache,source):
    data=Path(cache).read_bytes()
    if len(data)<16 or data[:4]!=importlib.util.MAGIC_NUMBER:return False
    try:return marshal.loads(data[16:])==compile(Path(source).read_bytes(),str(Path(source)),'exec')
    except (ValueError,TypeError,EOFError):return False


def bytecode_status(cache,source):
    data=Path(cache).read_bytes();stat=Path(source).stat()
    if bytecode_matches_source(cache,source):
        return dict(status='SOURCE_EQUIVALENT',requires_observed_source_fallback=False)
    if len(data)>=16 and data[:4]==importlib.util.MAGIC_NUMBER:
        flags,mtime,size=struct.unpack('<III',data[4:16])
        if flags==0 and (mtime!=int(stat.st_mtime)&0xffffffff or size!=stat.st_size&0xffffffff):
            return dict(status='STALE_TIMESTAMP_CACHE',requires_observed_source_fallback=True,
                cached_mtime=mtime,cached_size=size,source_mtime=int(stat.st_mtime),source_size=stat.st_size)
    return dict(status='UNVERIFIED',requires_observed_source_fallback=True)


def audit_stage(trace,allowed_files,runtime_roots,write_root,bootstrap):
    result=audit_opens(trace,allowed_files,runtime_roots,write_root)
    approved={str(Path(p).resolve()) for p in bootstrap}
    extras=result['forbidden_successes']
    result['bootstrap_exceptions']=[p for p in extras if p in approved]
    result['forbidden_successes']=[p for p in extras if p not in approved]
    result['passed']=not result['forbidden_successes'] and not result['unparsed_open_lines']
    return result

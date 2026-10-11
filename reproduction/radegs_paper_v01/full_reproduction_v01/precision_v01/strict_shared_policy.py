"""Fail-closed GPU0 policy using memory.free from one NVIDIA XML snapshot.

Reserved driver memory is not available. Do not infer free as total-used.
The original sealed shared wrapper remains unchanged.
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0, '/mnt/hdd1/u00134/radegs_paper_reproduction_v01/stage2/shared')
from shared_runner import GPU
import safety


def valid(g):
    try:
        values=[g[k] for k in ('total_mib','memory_mib','free_mib','util_percent')]
        return (all(type(x) is int for x in values) and g['total_mib']>0
                and 0<=g['memory_mib']<=g['total_mib']
                and 0<=g['free_mib']<=g['total_mib']-g['memory_mib']
                and 0<=g['util_percent']<=100)
    except (KeyError,TypeError):
        return False


def can_start(g):
    return (valid(g) and g.get('uuid')==GPU and g['util_percent']<=10
            and g['free_mib']>=12288)


def conflict(samples, selected, owned, baseline):
    if samples is None or selected!=GPU:
        return True
    g=next((g for g in samples if g.get('uuid')==selected),None)
    return (g is None or not valid(g) or g['free_mib']<2048
            or any(c['pid'] not in owned|baseline for c in g['contexts']))


def parse(raw):
    samples=safety.parse_gpu_xml(raw)
    if samples is None:
        return None
    try:
        nodes={n.findtext('uuid'):n for n in ET.fromstring(raw).findall('gpu')}
        for g in samples:
            n=nodes[g['uuid']]
            g['total_mib']=int(n.findtext('fb_memory_usage/total').split()[0])
            g['free_mib']=int(n.findtext('fb_memory_usage/free').split()[0])
            if not valid(g):
                return None
        return samples if len(samples)==1 and samples[0]['uuid']==GPU else None
    except (ET.ParseError,KeyError,TypeError,ValueError,AttributeError):
        return None


def query():
    try:
        result=subprocess.run(['nvidia-smi','--id='+GPU,'-q','-x'],
                              capture_output=True,text=True,timeout=20,check=True)
        return parse(result.stdout)
    except (OSError,subprocess.SubprocessError):
        return None

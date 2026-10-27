"""Serial bounded subprocesses; never reruns an existing completed output."""
import runtime
from pathlib import Path
import json
import subprocess
import sys

UNIT=runtime.ROOT/'units/unit_001'

def main():
    index=int(sys.argv[1]);p=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert runtime.sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    locks=json.loads((UNIT/'SOURCE_LOCK.json').read_text())
    for name,h in locks['files'].items():assert runtime.sha(UNIT/'delivery/code'/name)==h
    c=p['cameras'][index];view=c['view'];records=[]
    for state in ('baseline','spacing','paper_half'):
        argv=[sys.executable,'-B',str(UNIT/'delivery/code/linked_asset.py'),'render','--asset',str(UNIT/'delivery/assets'/state),
            '--out',str(UNIT/'renders'/view/state),'--camera',str(UNIT/'cameras'/(view+'.json'))]
        if state=='baseline':argv+=['--legacy',str(UNIT/'inputs/historical_asset')]
        receipt=UNIT/'logs'/f'view_{index}_{state}.json'
        wrapped=[sys.executable,'-B',str(Path(__file__).parent/'run_logged.py'),'--receipt',str(receipt),'--',*argv]
        r=subprocess.run(wrapped,timeout=580)
        records.append(dict(wrapper_returncode=r.returncode,child_receipt=str(receipt)))
        runtime.js(UNIT/f'VIEW_{index}_EXECUTION.json',records)
        if r.returncode:raise SystemExit(r.returncode)

if __name__=='__main__':main()

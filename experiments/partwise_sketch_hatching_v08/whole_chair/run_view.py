"""One bounded serial view stage, explicit v08 unit002 paths."""
import runtime
from pathlib import Path
import json,subprocess,sys
UNIT=runtime.ROOT/'units/unit_002'
def main():
    i=int(sys.argv[1]);p=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert runtime.sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert runtime.sha(UNIT/'DECISION.json')==p['decision_sha256']
    for n,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['cli_files'].items():assert runtime.sha(UNIT/'delivery/code'/n)==h
    c=p['cameras'][i];records=[]
    for state in p['states']:
        argv=[sys.executable,'-B',str(UNIT/'delivery/code/whole_asset.py'),'render','--asset',str(UNIT/'delivery/assets'/state),'--out',str(UNIT/'renders'/c['view']/state),'--camera',str(UNIT/'cameras'/(c['view']+'.json'))]
        receipt=UNIT/'logs'/f'view_{i}_{state}.json'
        wrapper=[sys.executable,'-B',str(Path(__file__).parent/'run_logged.py'),'--receipt',str(receipt),'--',*argv]
        r=subprocess.run(wrapper,timeout=580)
        records.append(dict(wrapper_returncode=r.returncode,child_receipt=str(receipt)));runtime.js(UNIT/f'VIEW_{i}_EXECUTION.json',records)
        if r.returncode:raise SystemExit(r.returncode)
if __name__=='__main__':main()

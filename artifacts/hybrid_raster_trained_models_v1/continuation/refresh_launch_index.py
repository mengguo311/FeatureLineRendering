"""Report actual completed and failed continuation launches without inferring success."""
import datetime,hashlib,json,os
from pathlib import Path
CONT=Path(__file__).resolve().parent
EXTERNAL=Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1')
rows=[];failed=[]
for p in sorted((EXTERNAL/'launchlogs').glob('*/EXIT.json')):
 v=json.loads(p.read_text())
 row={'path':str(p.parent),'scene':v['scene'],'phase':v['phase'],'exit_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'trace_sha256':v.get('trace_sha256'),'elapsed_seconds':v.get('elapsed_seconds'),'exit_code':v['exit_code']}
 (rows if v['completed'] else failed).append(row)
expected={(s,p) for s in ('materials','mic','ship') for p in ('render','media')}
actual={(r['scene'],r['phase']) for r in rows}
value={'schema':1,'expected_new_successful_launches':6,'launches':rows,'failed_attempts_preserved':failed,'complete':len(rows)==6 and actual==expected,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Only EXIT.completed true launches count; retained failures never relabeled PASS. Full independent trace/content validation remains separate.'}
p=CONT/'LAUNCH_INDEX.json';q=p.with_suffix('.partial');q.write_text(json.dumps(value,indent=2)+'\n');os.replace(q,p)
print(json.dumps({'complete':value['complete'],'successful_launches':len(rows),'failed_attempts':len(failed)}))

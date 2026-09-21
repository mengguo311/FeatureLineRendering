"""Read-only summary of recorded unittest executions, including retained failures."""
import json,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];art=ROOT/'artifacts/adaptive_mass_layered_probe'
rows=[]
for r in sorted(map(json.loads,(art/'TDD.jsonl').read_text().splitlines()),key=lambda r:r['sequence']):
 if 'unittest' not in r['command']:continue
 log=(ROOT/r['output']).read_text();m=re.search(r'Ran (\d+) tests? in ([\d.]+)s',log)
 rows.append(dict(sequence=r['sequence'],phase=r['phase'],label=r['label'],command=r['command'],log=r['output'],log_sha256=r['output_sha256'],exit_code=r['exit_code'],tests=int(m[1]) if m else None,seconds=float(m[2]) if m else None,skipped=int(re.search(r'OK \(skipped=(\d+)\)',log)[1]) if re.search(r'OK \(skipped=(\d+)\)',log) else 0,unittest_ok=bool(re.search(r'^OK(?: \(skipped=\d+\))?$',log,re.M))))
latest={r['label']:r for r in rows};full=latest['full_suite_all_integration'];traced=latest['full_suite_access_traced'];assert full['unittest_ok'] and full['tests']==196 and full['skipped']==0;assert traced['unittest_ok'] and traced['tests']==196 and traced['skipped']==1
result=dict(passed=True,latest_full=full,latest_access_traced_full=traced,nested_trace_note='Actual confined synthetic layout rendering is tested under its own strace in the untraced full suite and targeted GREEN; the same test is skipped under the outer tracer because nested ptrace is unsupported. Earlier failed attempts remain listed.',executions=rows)
(art/'TEST_SUMMARY.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='executions'},indent=2))

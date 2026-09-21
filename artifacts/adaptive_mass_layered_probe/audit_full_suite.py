"""Reuse the verifier's exact full-suite audit policy for an early trace check."""
import ast,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.corrected_audit import audit_policy
from scripts.verify_adaptive_mass_probe import sha
root=ROOT/'out/adaptive_mass_layered_probe';up=ROOT/'out/multiscene_foundation/vendor/gaussian-splatting'
tree=ast.parse((ROOT/'scripts/verify_adaptive_mass_probe.py').read_text())
node=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='suite_policy' for t in n.targets))
exec(compile(ast.Module(body=[node],type_ignores=[]),'<frozen suite audit policy>','exec'))
result={}
for p in sorted((root/'setup').glob('full_suite*.strace')):
    result[p.name]=audit_policy(p.read_text(),suite_policy,root/'setup',[str(ROOT),str(up)])
    result[p.name]['trace_sha256']=sha(p)
passed=all(r['passed'] for r in result.values())
(ROOT/'artifacts/adaptive_mass_layered_probe/FULL_SUITE_ACCESS_PREFLIGHT.json').write_text(json.dumps(dict(passed=passed,stages=result),sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(passed=passed,details={k:{f:v[f] for f in ['passed','forbidden_successes','unparsed_open_lines']} for k,v in result.items()}),indent=2))
raise SystemExit(0 if passed else 1)

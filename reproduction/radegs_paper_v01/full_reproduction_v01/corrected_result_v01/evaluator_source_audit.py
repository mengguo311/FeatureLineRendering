"""Audit the existing stage2 subprocess launcher patch separately from math."""
import ast,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from safety import sha256,atomic_json
HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');A=HDD/'sources/RaDe-GS';B=HDD/'sources/paper_text_precision_v01';OUT=HDD/'full_reproduction_v01/precision_v01/corrected_result_audit_v01'
a=ast.parse((A/'evaluate_dtu_mesh.py').read_text());b=ast.parse((B/'evaluate_dtu_mesh.py').read_text())
assert isinstance(b.body[0],ast.Import) and b.body[0].names[0].name=='subprocess'
assert isinstance(b.body[1],ast.Import) and b.body[1].names[0].name=='sys'
b.body=b.body[2:]
af=next(f for f in a.body if isinstance(f,ast.FunctionDef) and f.name=='evaluate_mesh');bf=next(f for f in b.body if isinstance(f,ast.FunctionDef) and f.name=='evaluate_mesh')
assert ast.dump(ast.Module(body=af.body[:-3],type_ignores=[]))==ast.dump(ast.Module(body=bf.body[:-1],type_ignores=[]))
old_launcher=ast.unparse(ast.Module(body=af.body[-3:],type_ignores=[]));new_launcher=ast.unparse(bf.body[-1]);assert 'subprocess.run' in new_launcher and 'check=True' in new_launcher and 'sys.executable' in new_launcher
bf.body=copy.deepcopy(af.body)
assert ast.dump(a)==ast.dump(b),'unexpected additional source change'
assert sha256(A/'dtu_eval/eval.py')==sha256(B/'dtu_eval/eval.py')
r={'outer_byte_identical':False,'inner_byte_identical':True,'outer_all_algorithm_and_parser_AST_identical':True,'only_outer_changes':'import subprocess/sys and replace shell/os.system launcher with subprocess.run using the same interpreter and check=True','old_launcher':old_launcher,'new_launcher':new_launcher,'files':{str(p):sha256(p) for p in [A/'evaluate_dtu_mesh.py',B/'evaluate_dtu_mesh.py',A/'dtu_eval/eval.py',B/'dtu_eval/eval.py']},'correction':'Earlier new invocation/preflight described evaluator as unchanged without distinguishing math from launcher. That wording is corrected here; old sealed records are preserved, not rewritten. Official metric mathematics is unchanged and inner evaluator byte-identical.','origin':'existing stage2 source patch; not modified during this slice','scientificdone':False}
atomic_json(OUT/'EVALUATOR_SOURCE_CORRECTION.json',r);print(json.dumps(r,indent=2))

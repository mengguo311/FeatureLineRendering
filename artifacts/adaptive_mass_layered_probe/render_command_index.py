"""Render the completed command ledger without changing its records."""
import json,shlex
from pathlib import Path
art=Path(__file__).resolve().parent;rows=sorted(map(json.loads,(art/'TDD.jsonl').read_text().splitlines()),key=lambda r:r['sequence'])
lines=['# Exact execution and TDD commands','','Commands ran in /home/u00134/3dgs_line/tier1 through record_command.py. Each entry contains the exact child argv, environment, source hashes, timestamps and protocol hash in TDD.jsonl. Concurrent jobs append on completion, so this index is sorted by allocated sequence. RED means a nonzero child exit was required; failed fixture/harness attempts are retained and explained in the report.','', 'Environment: PYTHONPATH=.:tests; PYTHONDONTWRITEBYTECODE=1; OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1; OMP_WAIT_POLICY=PASSIVE; CUDA_VISIBLE_DEVICES=1.','']
for r in rows:
 lines += [f"## {r['sequence']:03d} {r['phase']} {r['label']} (exit {r['exit_code']})",'', '```bash',shlex.join(r['command']),'```','',f"Command SHA256: `{r['command_sha256']}`",f"Log SHA256: `{r['output_sha256']}`",f"Log: [{Path(r['output']).name}](logs/{Path(r['output']).name})",f"UTC: {r['started_utc']} to {r['finished_utc']}",'']
(art/'COMMANDS.md').write_text('\n'.join(lines));print('Indexed',len(rows),'commands')

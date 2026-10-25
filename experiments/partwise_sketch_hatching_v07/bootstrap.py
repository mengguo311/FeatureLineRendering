"""One local replay bootstrap. Old package and installed environment stay read-only."""
import os,sys,json,hashlib,shutil,subprocess,time
from pathlib import Path
ROOT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07')
UNIT=ROOT/'units/unit_001'
OLD=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/delivery_package')
PY='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python'
HERE=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    start=time.monotonic(); package=ROOT/'replay_package'
    package.mkdir(exist_ok=False)
    inputs={str(p):sha(p) for p in sorted((OLD/'code').iterdir()) if p.is_file()}
    inputs.update({str(p):sha(p) for p in sorted((OLD/'data/lego').rglob('*')) if p.is_file()})
    inputs[str(OLD/'requirements.txt')]=sha(OLD/'requirements.txt')
    shutil.copytree(OLD/'code',package/'code')
    shutil.copytree(OLD/'data/lego',package/'data/lego')
    (package/'requirements.txt').write_text((OLD/'requirements.txt').read_text().rstrip()+'\nopen3d==0.20.0\n')
    (UNIT/'BOOTSTRAP_INPUTS.json').write_text(json.dumps(dict(original_files=inputs,python=PY,installed_nothing=True),indent=2)+'\n')
    # Experimental imports use an exact copy plus a separate v07-only runtime.
    vendor=HERE/'vendor'; shutil.copytree(OLD/'code',vendor)
    (HERE/'VENDOR_PROVENANCE.json').write_text(json.dumps(dict(source=str(OLD/'code'),files={p.name:sha(p) for p in (OLD/'code').iterdir() if p.is_file()}),indent=2)+'\n')
    calls=[('dependencies',[PY,'-B','-c','import numpy,scipy,plyfile,PIL,open3d; import importlib.metadata as m; print({k:m.version(k) for k in ["numpy","scipy","plyfile","Pillow","open3d"]})']),
           ('mapping',[PY,'-B',str(package/'code/linked_source_cli.py'),'mapping','--scene','lego','--ids','49033','174330']),
           ('cold_source',[PY,'-B',str(package/'code/linked_source_cli.py'),'render','--scene','lego','--out',str(UNIT/'cold_source'),'--verify']),
           ('cold_hybrid',[PY,'-B',str(package/'code/linked_source_cli.py'),'render','--scene','lego','--hybrid','--out',str(UNIT/'cold_hybrid'),'--verify'])]
    results=[]
    for label,cmd in calls:
        remaining=480-(time.monotonic()-start)
        if remaining<=0: break
        r=subprocess.run([sys.executable,'-B',str(HERE/'run_logged.py'),label,str(min(remaining,300)),*cmd])
        results.append(dict(stage=label,returncode=r.returncode))
        if r.returncode: break
    (UNIT/'BOOTSTRAP_STATUS.json').write_text(json.dumps(dict(stages=results,elapsed_seconds=time.monotonic()-start,engineering_only=True),indent=2)+'\n')
    print(json.dumps(results),flush=True)
    sys.exit(0 if len(results)==4 and all(x['returncode']==0 for x in results) else 1)
if __name__=='__main__': main()

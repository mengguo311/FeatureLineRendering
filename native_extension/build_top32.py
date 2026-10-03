"""Copy audited historical source, patch only contributor capacity, build locally."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'native_extension'
SOURCE=Path('/home/u00134/3dgs_line/hybrid_raster_evidence_v2/out/hybrid_raster_evidence_v2/native/patched')
MANIFEST=SOURCE.parent/'SOURCE_MANIFEST.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    out=OUT/'top32';out.mkdir(parents=True,exist_ok=True)
    reserve=2*1024**3;payload=2*1024**3
    if shutil.disk_usage(ROOT).free<reserve+payload:raise SystemExit('Disk reserve + predicted payload unavailable')
    manifest=json.loads(MANIFEST.read_text());files=manifest['files']['patched']
    for name,digest in files.items():
        p=SOURCE/name
        if sha(p)!=digest:raise RuntimeError('Historical source changed: '+name)
        q=out/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
    p=out/'cuda_rasterizer/render_forward.cu';before=p.read_text();after=before
    replacements={'int top_ids[4] = {-1, -1, -1, -1};':'constexpr int ATTR_TOPK = 32;\n    int top_ids[ATTR_TOPK];\n    for (int q=0; q<ATTR_TOPK; ++q) top_ids[q] = -1;', 'float top_w[4] = {0, 0, 0, 0};':'float top_w[ATTR_TOPK] = {};','float top_d[4] = {0, 0, 0, 0};':'float top_d[ATTR_TOPK] = {};','float3 top_n[4] = {};':'float3 top_n[ATTR_TOPK] = {};','rank < 4':'rank < ATTR_TOPK','int k = 3; k > rank':'int k = ATTR_TOPK-1; k > rank','int k = 0; k < 4; ++k':'int k = 0; k < ATTR_TOPK; ++k','int off = pix_id * 4 + k;':'int off = pix_id * ATTR_TOPK + k;'}
    for a,b in replacements.items():
        if a not in after:raise RuntimeError('Expected patch site missing: '+a)
        after=after.replace(a,b)
    p.write_text(after)
    import difflib
    (OUT/'top32.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/cuda_rasterizer/render_forward.cu',tofile='b/cuda_rasterizer/render_forward.cu')))
    patched_sha=sha(p)
    env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',CUDA_HOME='/usr/local/cuda',TORCH_CUDA_ARCH_LIST='8.6',MAX_JOBS='2',TMPDIR=str(OUT/'tmp'),XDG_CACHE_HOME=str(OUT/'cache'),TORCH_EXTENSIONS_DIR=str(OUT/'torch_extensions'),PATH='/home/u00134/bin/miniconda3/envs/vfsdgs/bin:/usr/local/cuda/bin:'+env.get('PATH',''))
    for key in ('TMPDIR','XDG_CACHE_HOME','TORCH_EXTENSIONS_DIR'):Path(env[key]).mkdir(parents=True,exist_ok=True)
    start=time.time()
    with (OUT/'build_top32.log').open('w') as log:
        proc=subprocess.run([sys.executable,'-B','setup.py','build_ext','--inplace'],cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT)
    rec=dict(returncode=proc.returncode,elapsed_seconds=time.time()-start,source_path=str(SOURCE),historical_manifest_sha256=sha(MANIFEST),original_forward_sha256=files['cuda_rasterizer/render_forward.cu'],patched_forward_sha256=patched_sha,patch_sha256=sha(OUT/'top32.patch'),topk=32,changes='Only top contribution array capacity/loops; RGB alpha depth traversal unchanged',estimated_max_write_bytes=payload,reserve_bytes=reserve)
    if proc.returncode==0:
        binaries=list((out/'diff_gaussian_rasterization').glob('_C*.so'));assert len(binaries)==1
        rec.update(library=str(binaries[0]),library_sha256=sha(binaries[0]))
    (OUT/'BUILD_TOP32.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec,indent=2),flush=True)
    raise SystemExit(proc.returncode)
if __name__=='__main__':main()

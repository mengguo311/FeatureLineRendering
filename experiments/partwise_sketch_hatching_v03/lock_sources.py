"""Pin implementation/input hashes after tests and commit, before candidate outputs."""
from runtime import *
import subprocess

def main():
    assert not (ROOT/'renders').exists()
    protocol=json.loads((ROOT/'PROTOCOL.json').read_text())
    files=dict(protocol['baseline_hashes'])
    for p in sorted(CODE.glob('*.py')):
        files[str(p)]=sha(p)
    for p in [DOC/'PROTOCOL.json',DOC/'BASELINE_ACCEPTANCE_ZH.md',ROOT/'PROTOCOL.json',ROOT/'audit/HEADROOM.json',ROOT/'audit/AUTHORED_CURVES.json',Path(FFMPEG)]:
        files[str(p)]=sha(p)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    assert branch=='partwise-sketch-hatching-p2-v03'
    write_json(ROOT/'SOURCE_LOCK.json',dict(files=files,implementation_commit=commit,protocol_commit='ef135f45',branch=branch,
                    frozen_before_renders=True,resources=resources()))
    write_json(ROOT/'runtime/git_sparse_failure.json',dict(command='git add docs/partwise_sketch_hatching_v03 experiments/partwise_sketch_hatching_v03',returncode=1,
                    error='New directories outside sparse-checkout definition; no commit occurred.',recovery='git add --sparse limited to authorized new directories, followed by local protocol commit ef135f45',scientific_effect='None; before all candidate outputs.'))
    update_status('SOURCE_LOCKED_READY_TO_RUN')
    print(json.dumps(dict(commit=commit,files=len(files))))

if __name__=='__main__': main()

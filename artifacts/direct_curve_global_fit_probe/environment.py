"""Administrative environment provenance; no scene inputs."""
import sys,json,platform,subprocess,hashlib
from pathlib import Path
import torch,numpy,scipy,cv2,PIL,imageio_ffmpeg
root=Path.cwd();art=root/'artifacts/direct_curve_global_fit_probe'
def command(argv):return subprocess.check_output(argv,text=True).strip()
r=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),torch=torch.__version__,torch_cuda=torch.version.cuda,cudnn=torch.backends.cudnn.version(),numpy=numpy.__version__,scipy=scipy.__version__,opencv=cv2.__version__,Pillow=PIL.__version__,ffmpeg=imageio_ffmpeg.get_ffmpeg_exe(),ffmpeg_version=command([imageio_ffmpeg.get_ffmpeg_exe(),'-version']),compiler=command(['g++','--version']),gpu=command(['nvidia-smi','--query-gpu=index,name,uuid,driver_version,memory.total','--format=csv']),head=command(['git','rev-parse','HEAD']),branch=command(['git','branch','--show-current']))
for key in ['ffmpeg']:
 r[key+'_sha256']=hashlib.sha256(Path(r[key]).read_bytes()).hexdigest()
(art/'ENVIRONMENT.json').write_text(json.dumps(r,sort_keys=True,indent=2)+'\n');print(json.dumps(r,indent=2))

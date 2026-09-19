"""Execute every unchanged repository test, with original repository read-only."""
import os,pathlib,sys,unittest
O=pathlib.Path(__file__).resolve().parents[1];R=O.parents[1];S=O/'setup/repository_suite'
os.environ.update(TMPDIR=str(S/'tmp'),CUDA_CACHE_DISABLE='1',PYTHONDONTWRITEBYTECODE='1',GIT_CONFIG_GLOBAL='/dev/null')
sys.path[:0]=[str(S),str(S/'tests')]
from src.foundation import restrict_filesystem
runtime=[R,pathlib.Path('/home/u00134/bin/miniconda3'),pathlib.Path('/usr'),pathlib.Path('/lib'),pathlib.Path('/lib64'),pathlib.Path('/etc'),pathlib.Path('/proc'),pathlib.Path('/sys'),pathlib.Path('/run'),pathlib.Path('/tmp')]
restrict_filesystem([p for p in runtime if p.exists()],[O,'/dev','/proc']);os.chdir(S)
suite=unittest.defaultTestLoader.discover(str(S/'tests'),pattern='test_*.py');result=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(not result.wasSuccessful())

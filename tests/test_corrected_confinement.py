import os,subprocess,sys,tempfile,textwrap,unittest
from pathlib import Path


class ConfinementTests(unittest.TestCase):
    def test_old_pca_control_is_available_after_file_only_confinement(self):
        code=textwrap.dedent('''
            import sys,importlib,numpy as np
            from pathlib import Path
            from src.corrected_probe import pca_control
            from src.foundation import restrict_filesystem
            from test_multiscene import CFG
            class Evidence:
                def observations(self,points):
                    return [dict(visible=np.ones(len(points),bool),dt=np.zeros(len(points))) for _ in range(4)]
            x,y=np.meshgrid(np.linspace(-.2,.2,12),np.linspace(-.2,.2,12))
            mu=np.c_[x.ravel(),y.ravel(),np.ones(x.size)]
            asset=dict(mu=mu,scale=np.full_like(mu,.03))
            sources=list(Path('src').resolve().glob('*.py'))
            runtime=[Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys')]
            restrict_filesystem([*sources,*[p.resolve() for p in runtime if p.exists()]],[Path(sys.argv[1]),'/dev'])
            importlib.invalidate_caches()
            result=pca_control(asset,Evidence(),CFG)
            assert len(result['accepted'])>0
        ''')
        with tempfile.TemporaryDirectory() as td:
            env=dict(os.environ,PYTHONPATH='.:tests',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
            result=subprocess.run([sys.executable,'-c',code,td],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            self.assertEqual(result.returncode,0,result.stdout)

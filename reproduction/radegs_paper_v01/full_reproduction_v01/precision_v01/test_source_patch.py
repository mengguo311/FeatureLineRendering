from pathlib import Path
import subprocess
import tempfile
import unittest
from source_patch import make_patch


class SourcePatchTests(unittest.TestCase):
    def replay(self,old,new):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);work=root/'work';work.mkdir()
            before=root/'before';after=root/'after';after.write_bytes(new)
            if old is not None:before.write_bytes(old);(work/'file.cu').write_bytes(old)
            patch=root/'patch.diff';patch.write_text(make_patch(before if old is not None else None,after,'file.cu'))
            check=subprocess.run(['git','apply','--check',str(patch)],cwd=work,capture_output=True,text=True)
            self.assertEqual(check.returncode,0,check.stderr)
            subprocess.run(['git','apply',str(patch)],cwd=work,check=True,capture_output=True)
            self.assertEqual((work/'file.cu').read_bytes(),new)

    def test_missing_final_newline_roundtrip(self):self.replay(b'old\n}',b'new\n}')
    def test_new_file_missing_final_newline_roundtrip(self):self.replay(None,b'header\n}')
    def test_changed_final_newline_roundtrip(self):self.replay(b'old\n}',b'new\n}\n')


if __name__=='__main__':unittest.main(verbosity=2)

import unittest,tempfile,pathlib
class Verification(unittest.TestCase):
 def test_bootstrap_cannot_excuse_post_confinement_scientific_read(self):
  import cc_verify
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);output=root/'output';output.mkdir();policy_path=output/'allowlist.json';config=root/'config.json';config.write_text('{}');photo=root/'F.png';photo.write_bytes(b'x');bad=root/'DEV.png';bad.write_bytes(b'y')
   policy=dict(readonly=[str(photo)],writable=[str(output)])
   lines=[f'1 openat(AT_FDCWD, "{config}", O_RDONLY) = 3<{config}>',f'1 openat(AT_FDCWD, "{policy_path}", O_WRONLY|O_CREAT) = 3<{policy_path}>',f'1 openat(AT_FDCWD, "{photo}", O_RDONLY) = 3<{photo}>']
   r=cc_verify.audit_one('\n'.join(lines),policy,output,[config]);self.assertTrue(r['passed'])
   lines.append(f'1 openat(AT_FDCWD, "{config}", O_RDONLY) = 3<{config}>');self.assertFalse(cc_verify.audit_one('\n'.join(lines),policy,output,[config])['passed'])
   lines[-1]=f'1 openat(AT_FDCWD, "{bad}", O_RDONLY) = 3<{bad}>';self.assertFalse(cc_verify.audit_one('\n'.join(lines),policy,output,[config])['passed'])
 def test_inventory_detects_added_missing_mutated_and_symlinks(self):
  import cc_verify
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);(root/'a').write_text('a');(root/'link').symlink_to('/not/read')
   m=cc_verify.inventory(root);self.assertEqual(len(m),2);self.assertTrue(cc_verify.verify_inventory(root,m))
   (root/'a').write_text('b');self.assertFalse(cc_verify.verify_inventory(root,m))
   (root/'a').write_text('a');(root/'extra').write_text('x');self.assertFalse(cc_verify.verify_inventory(root,m))
if __name__=='__main__':unittest.main()

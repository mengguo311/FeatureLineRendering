"""Invalid browser style requests must not commit partial cross-hatch edits."""
import runtime
from runtime import OUTPUT_ROOT
from pathlib import Path
import json,threading,unittest,urllib.request,urllib.error,tempfile
from http.server import HTTPServer
from viewer import Editor,Handler

class CrossHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=OUTPUT_ROOT/'units/unit_013/test_work')
        cls.root=Path(cls.temp.name)
        cls.editor=Editor(OUTPUT_ROOT/'units/unit_012/portable_demo/assets/chair',cls.root/'session')
        class LocalHandler(Handler):pass
        LocalHandler.editor=cls.editor
        cls.server=HTTPServer(('127.0.0.1',0),LocalHandler)
        cls.thread=threading.Thread(target=cls.server.serve_forever);cls.thread.start()
        cls.url='http://127.0.0.1:'+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.thread.join();cls.server.server_close();cls.temp.cleanup()
    def test_invalid_cross_settings_do_not_commit(self):
        before=self.editor.record.copy();folders=set(self.root.rglob('*'))
        payload=dict(region=2,**before['camera'],**before['styles']['2'])
        for invalid in (dict(cross_enabled='true'),dict(cross_angle=0),dict(cross_spacing=-.1)):
            req=urllib.request.Request(self.url+'/render',data=json.dumps(dict(payload,**invalid)).encode(),headers={'Content-Type':'application/json'})
            with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req,timeout=30)
            self.assertEqual(e.exception.code,422)
            self.assertEqual(self.editor.record,before)
            self.assertEqual(set(self.root.rglob('*')),folders)

if __name__=='__main__':unittest.main(verbosity=2)

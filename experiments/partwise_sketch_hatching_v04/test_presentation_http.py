"""Real saved-Chair HTTP behavior; the missing export route is the initial red."""
import runtime
from runtime import OUTPUT_ROOT
from pathlib import Path
import json,threading,unittest,urllib.request,urllib.error
from http.server import HTTPServer
from viewer import Editor,Handler

class ExportHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        cls.root=OUTPUT_ROOT/'units/unit_012/tests'/('http_'+str(os.getpid()))
        cls.root.mkdir(parents=True)
        cls.editor=Editor(OUTPUT_ROOT/'units/unit_011/portable_demo/assets/chair',cls.root/'session')
        class LocalHandler(Handler):pass
        LocalHandler.editor=cls.editor
        cls.server=HTTPServer(('127.0.0.1',0),LocalHandler)
        cls.thread=threading.Thread(target=cls.server.serve_forever);cls.thread.start()
        cls.url='http://127.0.0.1:'+str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.thread.join();cls.server.server_close()

    def post(self,body):
        req=urllib.request.Request(self.url+'/presentation',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=120) as r:return r.status,json.loads(r.read())
        except urllib.error.HTTPError as e:return e.code,json.loads(e.read())

    def test_current_png_download_is_the_actual_render(self):
        code,data=self.post(dict(kind='image',revision=0))
        self.assertEqual(code,200,data)
        with urllib.request.urlopen(self.url+data['png']) as r:png=r.read()
        self.assertEqual(png,(self.root/'session/view_0000/frame_000_image.png').read_bytes())
        self.assertEqual(self.editor.revision,0)

    def test_invalid_request_leaves_state_and_exports_unchanged(self):
        before=set(self.root.rglob('PRESENTATION.json'))
        for bad in ({'kind':'unknown','revision':0},{'kind':'orbit','revision':99},{'kind':'image','revision':0,'frames':999}):
            code,_=self.post(bad);self.assertEqual(code,422)
        self.assertEqual(before,set(self.root.rglob('PRESENTATION.json')))
        self.assertEqual(self.editor.revision,0)

if __name__=='__main__':unittest.main(verbosity=2)

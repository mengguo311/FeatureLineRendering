import test from 'node:test';import assert from 'node:assert/strict';import {mkdtemp,writeFile,rm} from 'node:fs/promises';import {tmpdir} from 'node:os';import path from 'node:path';import {gzipSync} from 'node:zlib';
let s={};try{s=await import('../server.mjs')}catch{}
test('loopback server transparently serves gzip binary and health, rejects traversal',async()=>{
 assert.equal(typeof s.createServer,'function');const root=await mkdtemp(path.join(process.env.TMPDIR||tmpdir(),'demo-test-'));await writeFile(path.join(root,'geometry.bin.gz'),gzipSync(Buffer.from(new Float32Array([1,2,3]).buffer)));
 const server=s.createServer(root);await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}`;
 try{assert.equal((await fetch(base+'/health')).status,200);const r=await fetch(base+'/geometry.bin');assert.equal(r.headers.get('content-encoding'),'gzip');assert.deepEqual([...new Float32Array(await r.arrayBuffer())],[1,2,3]);assert.equal((await fetch(base+'/%2e%2e%2fetc/passwd')).status,403);}finally{await new Promise(r=>server.close(r));await rm(root,{recursive:true});}
});

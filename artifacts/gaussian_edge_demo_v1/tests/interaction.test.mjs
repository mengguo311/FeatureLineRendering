import test from 'node:test';import assert from 'node:assert/strict';import * as c from '../public/core.mjs';
test('native coordinates, rectangle/line pixels, wxyz kernel, background original IDs, lock and complete export',()=>{
 assert.equal(typeof c.nativePoint,'function');assert.deepEqual(c.nativePoint(250,150,{left:50,top:50,width:400,height:400}),{x:400,y:200});
 assert.deepEqual(c.roiPixels([{x:0,y:0},{x:1,y:1}],'rectangle',1,3,3),[0,1,3,4]);
 assert.ok(c.roiPixels([{x:0,y:0},{x:2,y:2}],'brush',1,3,3).includes(4));
 const g=new Float32Array([1,2,3,.1,.2,.3,.7,.1,.2,.3,1,0,0,.8]);const t=c.kernelTransform(g,0,2);assert.ok(Math.abs(t.quaternion[0]-.1)<1e-6);assert.ok(Math.abs(t.quaternion[3]-.7)<1e-6);assert.ok(Math.abs(t.scale[1]-.4)<1e-6);
 assert.deepEqual(c.backgroundIDs(7,3),[0,3,6]);
 assert.deepEqual(c.frameTransition({locked:true,selected:[2,0],pixels:[4]}).selected,[2,0]);assert.deepEqual(c.frameTransition({locked:false,selected:[2],pixels:[4]}).selected,[]);
 const x=c.exportSelection({scene:'s',frame:'F001',selected:[2,0],settings:{mode:'brush'},manifest:{source_commit:'abc',estimator:'TOP4-TRUNCATED'}});assert.deepEqual(x.original_ids,[0,2]);assert.equal(x.provenance.source_commit,'abc');assert.equal(x.settings.mode,'brush');
});

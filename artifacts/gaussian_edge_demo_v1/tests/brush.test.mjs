import test from 'node:test';import assert from 'node:assert/strict';import * as c from '../public/core.mjs';
test('brush sums real TOP4 weights over repeated IDs and retains unknown status',()=>{
 assert.equal(typeof c.brushSelection,'function');
 const ids=new Int32Array([2,0,-1,-1,1,2,-1,-1,0,1,-1,-1]);const weights=new Float32Array([.8,.2,0,0,.6,.4,0,0,.9,.1,0,0]);const signals=new Uint8Array(21);signals[3]=255;signals[10]=0;signals[17]=255;
 const scores=new Float32Array(36);scores[8]=1;scores[20]=1;scores[33]=1;
 const r=c.brushSelection({ids,weights,signals,scores,pixels:[0,1,2],category:'union',contributionCutoff:0,evidenceCutoff:0,minScore:.6,percent:100});
 assert.deepEqual(r.ids,[0,2]);assert.ok(Math.abs(r.values.get(2).score-2/3)<1e-6);assert.equal(r.values.get(2).unknown,true);assert.ok(Math.abs(r.values.get(1).score-1/7)<1e-6);
 assert.deepEqual(c.brushSelection({ids,weights,signals,scores,pixels:[0,1,2],category:'union',contributionCutoff:.5,evidenceCutoff:.5,minScore:0,percent:100}).ids,[0,2]);
});

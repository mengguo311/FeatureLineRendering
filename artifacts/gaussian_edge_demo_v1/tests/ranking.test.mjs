import test from 'node:test';
import assert from 'node:assert/strict';
let core={}; try{core=await import('../public/core.mjs')}catch{}
test('global ranking uses eligible rows, category, ceil density and original ID tie-break',()=>{
 assert.equal(typeof core.rankGlobal,'function');
 const scores=new Float32Array(5*12); for(let i=0;i<5;i++){scores[i*12+8]=i!==3?1:0;scores[i*12+1]=[.5,.9,.5,1,.2][i];scores[i*12+3]=[.1,.2,.9,1,.8][i]}
 assert.deepEqual(core.rankGlobal(scores,{method:'enhanced',category:'union',percent:60,minScore:0}),[1,0,2]);
 assert.deepEqual(core.rankGlobal(scores,{method:'enhanced',category:'color',percent:50,minScore:.85}),[2]);
});

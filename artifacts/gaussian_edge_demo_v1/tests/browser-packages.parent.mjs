import {chromium} from 'playwright';
import {spawn} from 'node:child_process';import assert from 'node:assert/strict';import {writeFile} from 'node:fs/promises';
const ROOT='/Users/menakuniay/next_npr_results/gaussian_edge_demo_distributions';
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--no-sandbox']});const results=[];
try{for(const [index,scene] of ['mic','materials'].entries()){
 const dir=ROOT+'/gaussian_edge_demo_'+scene;const server=spawn(process.execPath,['server.mjs'],{cwd:dir,env:{...process.env,PORT:String(8901+index)}});
 try{
  const url=await new Promise((resolve,reject)=>{server.stdout.on('data',d=>{const m=String(d).match(/http:\/\/127\.0\.0\.1:\d+/);if(m)resolve(m[0]);});server.on('error',reject);server.on('exit',c=>reject(Error('server exit '+c)));});
  const page=await browser.newPage({viewport:{width:1440,height:1100}});const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  await page.goto(url);await page.waitForFunction(s=>window.demo?.state.ready&&!window.demo.state.busy&&window.demo.state.scene.id===s,scene,{timeout:60000});assert.equal(await page.locator('#scene option').count(),1);assert.equal(await page.locator('#frame option').count(),3);assert.equal(await page.evaluate(()=>window.demo.renderer.getContext().isContextLost()),false);
  await page.click('#preset');for(const [id,value] of [['percent',100],['brushRadius',1],['minScore',0],['contributionCutoff',0],['evidenceCutoff',0]])await page.locator('#'+id).evaluate((e,v)=>{e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}));},String(value));
  const p=await page.evaluate(()=>{const s=window.demo.state;for(let p=0;p<640000;p++)if(s.signals[p*7+3]>100&&s.weights[p*4]>.05)return{x:p%800,y:Math.floor(p/800)};});const box=await page.locator('#imageCanvas').boundingBox();await page.mouse.click(box.x+(p.x+.5)*box.width/800,box.y+(p.y+.5)*box.height/800);
  const check=await page.evaluate(p=>{const s=window.demo.state;let expected=new Map();for(let y=p.y-1;y<=p.y+1;y++)for(let x=p.x-1;x<=p.x+1;x++){if((x-p.x)**2+(y-p.y)**2>1||x<0||y<0||x>=800||y>=800)continue;let pixel=y*800+x,e=s.signals[pixel*7+3]/255;for(let k=0;k<4;k++){let id=s.ids[pixel*4+k],w=s.weights[pixel*4+k];if(id<0||w<=0)continue;let a=expected.get(id)||{den:0,num:0};a.den+=w;a.num+=w*e;expected.set(id,a);}}let ids=[...expected.keys()].filter(i=>expected.get(i).num>0).sort((a,b)=>expected.get(b).num/expected.get(b).den-expected.get(a).num/expected.get(a).den||a-b);return{actual:s.selected,expected:ids,centerIncluded:s.pixels.includes(p.y*800+p.x),geometryCount:s.scene.count,rendered:s.selected.length};},p);
  assert.deepEqual(check.actual,check.expected);assert.ok(check.centerIncluded&&check.actual.length>0);assert.deepEqual(errors,[]);results.push({scene,passed:true,independently_verified_selected_ids:check.actual,kernel_count:check.geometryCount,console_errors:errors});await page.close();
 }finally{server.kill();await new Promise(r=>server.once('exit',r));}
}}finally{await browser.close();}
await writeFile(ROOT+'/BROWSER_PACKAGES_VERIFIED.json',JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));

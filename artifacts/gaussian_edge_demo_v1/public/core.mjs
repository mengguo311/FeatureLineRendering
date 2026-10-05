export function nativePoint(x,y,r){return {x:Math.max(0,Math.min(799,Math.floor((x-r.left)*800/r.width))),y:Math.max(0,Math.min(799,Math.floor((y-r.top)*800/r.height)))};}
export function roiPixels(path,tool='brush',radius=8,width=800,height=800){
 const set=new Set();if(!path.length)return [];
 const add=(x,y)=>{if(x>=0&&y>=0&&x<width&&y<height)set.add(y*width+x);};
 if(tool==='rectangle'){const a=path[0],b=path.at(-1);for(let y=Math.min(a.y,b.y);y<=Math.max(a.y,b.y);y++)for(let x=Math.min(a.x,b.x);x<=Math.max(a.x,b.x);x++)add(x,y);}
 else{const dab=(cx,cy)=>{for(let y=Math.floor(cy-radius);y<=Math.ceil(cy+radius);y++)for(let x=Math.floor(cx-radius);x<=Math.ceil(cx+radius);x++)if((x-cx)**2+(y-cy)**2<=radius**2)add(x,y);};dab(path[0].x,path[0].y);for(let i=1;i<path.length;i++){const a=path[i-1],b=path[i],n=Math.max(Math.abs(b.x-a.x),Math.abs(b.y-a.y),1);for(let j=0;j<=n;j++)dab(a.x+(b.x-a.x)*j/n,a.y+(b.y-a.y)*j/n);}}
 return [...set].sort((a,b)=>a-b);
}
export function kernelTransform(g,id,scale=1){const o=id*14;return {position:Array.from(g.slice(o,o+3)),scale:Array.from(g.slice(o+3,o+6),v=>v*scale),quaternion:[g[o+7],g[o+8],g[o+9],g[o+6]],color:Array.from(g.slice(o+10,o+13)),opacity:g[o+13]};}
export function backgroundIDs(count,step=1){return Array.from({length:Math.ceil(count/step)},(_,i)=>i*step);}
export function frameTransition({locked,selected}){return {selected:locked?[...selected]:[],pixels:[]};}
export function exportSelection({scene,frame,selected,settings,manifest}){return {version:1,scene,frame,original_ids:[...selected].sort((a,b)=>a-b),selected_count:selected.length,settings:{...settings},provenance:{source_commit:manifest.source_commit,estimator:manifest.estimator,ranking:'frozen F scores; brush is exploratory cached per-view selection',limitations:'TOP4 truncated; omitted contributions unknown; kernel viewer is not native 3DGS rendering'}};}
export function brushSelection({ids,weights,signals,scores,pixels,category='union',contributionCutoff=0,evidenceCutoff=0,minScore=0,percent=100}){
 const values=new Map(),channel={color:0,geometry:1,outline:2,union:3}[category];
 for(const p of new Set(pixels)){const e=signals[p*7+channel]/255;
  for(let k=0;k<4;k++){const i=ids[p*4+k],w=weights[p*4+k];if(i<0||i>=scores.length/12||!(w>0)||w<contributionCutoff)continue;
   const v=values.get(i)||{mass:0,numerator:0,unknown:scores[i*12+9]===1};v.mass+=w;v.numerator+=w*(e>=evidenceCutoff?e:0);values.set(i,v);
  }
 }
 for(const v of values.values())v.score=v.numerator/v.mass;
 const ranked=[...values.keys()].sort((a,b)=>values.get(b).score-values.get(a).score||a-b);
 return {ids:ranked.slice(0,Math.ceil(ranked.length*percent/100)).filter(i=>values.get(i).numerator>0&&values.get(i).score>=minScore),values};
}
export const categoryOffset={union:0,color:2,geometry:4,outline:6};
export function rankGlobal(scores,{method='enhanced',category='union',percent=5,minScore=0}={}){
 const offset=categoryOffset[category]+(method==='enhanced'?1:0),ids=[];
 for(let i=0;i<scores.length/12;i++)if(scores[i*12+8]===1)ids.push(i);
 ids.sort((a,b)=>scores[b*12+offset]-scores[a*12+offset]||a-b);
 return ids.slice(0,Math.ceil(ids.length*percent/100)).filter(i=>scores[i*12+offset]>=minScore);
}

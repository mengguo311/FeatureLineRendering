import http from 'node:http';import path from 'node:path';import {fileURLToPath} from 'node:url';import {stat} from 'node:fs/promises';import {createReadStream} from 'node:fs';
const ROOT=path.dirname(fileURLToPath(import.meta.url));
export function createServer(root=ROOT){return http.createServer(async(req,res)=>{
 try{let p=decodeURIComponent(req.url.split('?')[0]);if(p==='/health'){res.writeHead(200,{'Content-Type':'application/json'});return res.end(JSON.stringify({ok:true,read_only:true}));}if(p.includes('..')||p.includes('\\')){res.writeHead(403);return res.end('Forbidden');}
 if(p==='/')p='/public/index.html';else if(p.startsWith('/vendor/'))p='/node_modules/'+p.slice(8);else if(!p.startsWith('/data/')&&!p.startsWith('/node_modules/'))p='/public'+p;
 // Unit contract permits standalone binary roots; app assets remain fixed.
 let f=path.join(root,p);if(root!==ROOT&&p.startsWith('/public/'))f=path.join(root,p.slice(8));
 let zipped=false;try{await stat(f)}catch{if(f.endsWith('.bin')){f+='.gz';await stat(f);zipped=true;}else throw Error('missing');}
 const ext=zipped?'.bin':path.extname(f),mime={'.html':'text/html; charset=utf-8','.mjs':'text/javascript','.js':'text/javascript','.css':'text/css','.json':'application/json','.jpg':'image/jpeg','.jpeg':'image/jpeg','.bin':'application/octet-stream','.gz':'application/octet-stream'}[ext]||'application/octet-stream';
 res.writeHead(200,{'Content-Type':mime,'Cache-Control':'no-cache',...(zipped?{'Content-Encoding':'gzip'}:{})});createReadStream(f).pipe(res);
 }catch{res.writeHead(404);res.end('Not found');}
});}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){const server=createServer();let port=Number(process.env.PORT||8765);server.on('error',e=>{if(e.code==='EADDRINUSE'){port++;server.listen(port,'127.0.0.1')}else throw e});server.on('listening',()=>console.log(`http://127.0.0.1:${server.address().port}`));server.listen(port,'127.0.0.1');}

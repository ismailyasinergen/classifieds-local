'use strict';
// Synthetic HTTP fixture; never imports capture or repository code.
const http=require('node:http');
let mode='healthy',active=0,maxActive=0,requests=0;
const server=http.createServer((req,res)=>{
 active++;requests++;maxActive=Math.max(maxActive,active);
 res.on('close',()=>active--);
 process.send({type:'request',at:Date.now(),requests});
 if(mode==='hang')return;
 if(mode==='http_error'){res.writeHead(503,{'Set-Cookie':'private-cookie-canary'});return res.end('private-body-canary');}
 if(mode==='malformed')return res.end('{private-body-canary');
 if(mode==='oversize')return res.end('private-body-canary'.repeat(200));
 if(mode==='redirect'){res.writeHead(302,{Location:'http://example.invalid/private-cookie-canary'});return res.end();}
 res.end('{"status":"ok"}');
});
process.on('message',m=>{
 if(m.type==='mode'){mode=m.mode;process.send({type:'mode',mode});}
 if(m.type==='stats')process.send({type:'stats',active,maxActive,requests});
 if(m.type==='stop'){server.closeAllConnections();server.close(()=>process.disconnect());}
});
server.listen(0,'127.0.0.1',()=>process.send({type:'ready',port:server.address().port}));

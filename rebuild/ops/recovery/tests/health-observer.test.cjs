'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),{fork}=require('node:child_process'),path=require('node:path'),net=require('node:net');
const {startHealthObservation}=require('../health-observer.cjs');
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function fixture(t){
 const child=fork(path.join(__dirname,'health-server.cjs'),[],{execArgv:[],stdio:['ignore','ignore','ignore','ipc']});
 const messages=[];child.on('message',m=>messages.push(m));
 const next=type=>new Promise((resolve,reject)=>{const timer=setTimeout(()=>{child.off('message',fn);reject(Error('fixture_deadline'));},3000);const fn=m=>{if(m.type===type){clearTimeout(timer);child.off('message',fn);resolve(m);}};child.on('message',fn);});
 const ready=await next('ready');
 t.after(async()=>{if(child.connected){child.send({type:'stop'});await new Promise(r=>child.once('exit',r));}});
 return {port:ready.port,messages,next,async mode(mode){const p=next('mode');child.send({type:'mode',mode});await p;},async stats(){const p=next('stats');child.send({type:'stats'});return p;}};
}
function observe(t,port,options={}){const o=startHealthObservation({targets:[{label:'synthetic',port}],intervalMs:80,timeoutMs:160,maxDurationMs:3000,...options});t.after(()=>o.stop());return o;}
test('healthy samples have safe timestamps, monotonic duration and immutable closed receipts',async t=>{
 const s=await fixture(t),o=observe(t,s.port);const initial=await o.ready;assert.equal(initial[0].category,null);
 const report=await o.stop();assert.equal(report.status,'complete');assert.equal(report.records.length,1);
 const r=report.records[0];assert.equal(r.http,200);assert.equal(r.target,'synthetic');assert(r.endedMonoMs>=r.startedMonoMs);assert(r.durationMs>=0);assert(Date.parse(r.endedAt)>=Date.parse(r.startedAt));
 const saved=JSON.stringify(report);await delay(100);assert.equal(JSON.stringify(report),saved);assert(Object.isFrozen(report.records[0]));
});
for(const [mode,category,status] of [['hang','timeout',null],['http_error','http_error',503],['malformed','invalid_response',200],['oversize','invalid_response',200],['redirect','http_error',302]])test('classifies '+mode+' without response/header/exception disclosure',async t=>{
 const s=await fixture(t);await s.mode(mode);const o=observe(t,s.port),rows=await o.ready;assert.equal(rows[0].category,category);assert.equal(rows[0].http,status);
 const report=await o.stop();assert(!JSON.stringify(report).includes('private-'));assert(!JSON.stringify(report).includes('example.invalid'));
 if(mode==='hang')assert(rows[0].durationMs>=140);
});
test('real connection refusal stays distinct from timeout',async t=>{
 const server=net.createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));const port=server.address().port;await new Promise(r=>server.close(r));
 const o=observe(t,port);assert.equal((await o.ready)[0].category,'connection_refused');await o.stop();
});
test('observer keeps sampling while executor is synchronously blocked',async t=>{
 const s=await fixture(t),o=observe(t,s.port);await o.ready;
 const start=Date.now();Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,400);const end=Date.now();
 const report=await o.stop();assert(report.records.filter(r=>Date.parse(r.startedAt)>start&&Date.parse(r.endedAt)<end).length>=2);
 assert.equal((await s.stats()).maxActive,1);
});
test('stop aborts pending request once, awaits close and cannot append later',async t=>{
 const s=await fixture(t),o=observe(t,s.port);await o.ready;await s.mode('hang');await s.next('request');
 const start=performance.now(),report=await o.stop();assert(performance.now()-start<2500);
 assert.equal(report.records.at(-1).category,'shutdown_cancelled');assert.equal(report.startedCount,report.completedCount);
 assert.equal((await s.stats()).maxActive,1);assert.deepEqual(await o.stop(),report);
});
test('unexpected observer death is incomplete and accounted for, not healthy success',async t=>{
 const s=await fixture(t),o=observe(t,s.port);await o.ready;await s.mode('hang');await s.next('request');process.kill(o.pid,'SIGKILL');
 const report=await o.stop();assert.equal(report.status,'incomplete');assert.equal(report.error,'observer_exit');assert(report.records.some(r=>r.category==='observer_exit'));
});
test('slow requests skip slots without overlap or invented measurements',async t=>{
 const s=await fixture(t);await s.mode('hang');const o=observe(t,s.port);await o.ready;const report=await o.stop();
 assert(report.records[0].skippedSlots>=1);assert.equal((await s.stats()).maxActive,1);assert.equal(report.records.length,1);
});
test('worker receives no inherited secret or Node preload environment',async t=>{
 const s=await fixture(t),Module=require('node:module'),load=Module._load;let options;
 Module._load=function(name,...args){if(name==='node:child_process')return {fork(file,args,opts){options=opts;return fork(file,args,opts);}};return load.call(this,name,...args);};
 const file=require.resolve('../health-observer.cjs');delete require.cache[file];let start;
 try{start=require(file).startHealthObservation;}finally{Module._load=load;}
 const old=process.env.RESTIC_PASSWORD;process.env.RESTIC_PASSWORD='private-password-canary';
 try{const o=start({targets:[{label:'synthetic',port:s.port}],intervalMs:80,timeoutMs:160,maxDurationMs:3000});t.after(()=>o.stop());await o.ready;const report=await o.stop();
  assert(Object.keys(options.env).every(k=>['SystemRoot','WINDIR'].includes(k)));assert.deepEqual(options.execArgv,[]);
  assert(!JSON.stringify(options).includes('private-password-canary'));assert(!JSON.stringify(report).includes('private-password-canary'));
 }finally{if(old===undefined)delete process.env.RESTIC_PASSWORD;else process.env.RESTIC_PASSWORD=old;}
});
for(const failure of [false,true])test('real observer closes before capture entry persists '+(failure?'failure':'success'),async t=>{
 const a=await fixture(t),b=await fixture(t),Module=require('node:module'),load=Module._load;
 const baseline={runtime:[],git:{},volumes:[],networkIds:[],protected:[]};let saved,releaseCount=0;
 const mocks={'node:fs':{readFileSync:()=>JSON.stringify(baseline),writeFileSync:(file,bytes)=>{saved=JSON.parse(bytes);}},
  './task6-gate.cjs':{verifyReview:()=> 'a'.repeat(64)},'./inspect.cjs':{developer:process.cwd(),inspectBaseline:()=>baseline},
  './safe-process.cjs':{acquireLock:()=>()=>{releaseCount++;}},'./repository.cjs':{prepareRepository(){throw Error('real_repository_forbidden');}},
  './health-observer.cjs':{startHealthObservation:()=>startHealthObservation({targets:[{label:'original',port:a.port},{label:'developer',port:b.port}],intervalMs:80,timeoutMs:160,maxDurationMs:3000})},
  './original-capture.cjs':{async captureOriginal(){Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,300);if(failure)throw Error('synthetic_capture_failure');return {status:'committed'};}}};
 Module._load=function(name,...args){return mocks[name]||load.call(this,name,...args);};let main;
 try{const file=require.resolve('../task6-original.cjs');delete require.cache[file];main=require(file).main;}finally{Module._load=load;}
 const log=console.log,exit=process.exitCode;console.log=()=>{};let result;
 try{result=await main();assert.equal(process.exitCode,failure?1:exit);}finally{console.log=log;process.exitCode=exit;}
 assert.equal(result.status,failure?'failed':'committed');assert.equal(result.healthObservation.status,'complete');assert(result.health.length>=6);
 assert.deepEqual(saved,result);assert.equal(releaseCount,1);const receipt=JSON.stringify(saved);await delay(100);assert.equal(JSON.stringify(result),receipt);
});
test('fast and slow targets progress independently with one initial sample each',async t=>{
 const a=await fixture(t),b=await fixture(t);await b.mode('hang');
 const o=startHealthObservation({targets:[{label:'original',port:a.port},{label:'developer',port:b.port}],intervalMs:60,timeoutMs:250,maxDurationMs:3000});t.after(()=>o.stop());
 const initial=await o.ready;assert.deepEqual(initial.map(r=>r.target).sort(),['developer','original']);
 const report=await o.stop();assert(report.records.filter(r=>r.target==='original').length>=3);assert.equal(initial.find(r=>r.target==='developer').category,'timeout');
 assert.equal((await a.stats()).maxActive,1);assert.equal((await b.stats()).maxActive,1);assert.equal(report.startedCount,report.completedCount);
});
for(const mode of ['contradiction','duplicate_initial','timestamp','private_field','record_loss','ignore_stop'])test('IPC refuses '+mode+' without leaking child data',async t=>{
 const Module=require('node:module'),load=Module._load;
 Module._load=function(name,...args){if(name==='node:child_process')return {fork(file,args,opts){return fork(path.join(__dirname,'health-protocol-worker.cjs'),[mode],opts);}};return load.call(this,name,...args);};
 let start;try{const file=require.resolve('../health-observer.cjs');delete require.cache[file];start=require(file).startHealthObservation;}finally{Module._load=load;}
 const o=start({targets:[{label:'original',port:31001},{label:'developer',port:31002}],intervalMs:80,timeoutMs:160,maxDurationMs:3000});t.after(()=>o.stop());
 if(mode==='ignore_stop'){await delay(100);}else await o.ready;
 const report=await o.stop();assert.equal(report.error,mode==='ignore_stop'?'observer_stop_timeout':'observer_protocol_error');
 assert.equal(report.status,'incomplete');assert(!JSON.stringify(report).includes('private-body-canary'));
});
test('observer own event-loop delay is marked separately and missed slots are not backfilled',async t=>{
 const s=await fixture(t),Module=require('node:module'),load=Module._load;
 Module._load=function(name,...args){if(name==='node:child_process')return {fork(file,args,opts){return fork(file,args,{...opts,execArgv:['--require',path.join(__dirname,'health-delay-preload.cjs')]});}};return load.call(this,name,...args);};
 let start;try{const file=require.resolve('../health-observer.cjs');delete require.cache[file];start=require(file).startHealthObservation;}finally{Module._load=load;}
 const o=start({targets:[{label:'synthetic',port:s.port}],intervalMs:60,timeoutMs:160,maxDurationMs:3000});t.after(()=>o.stop());await o.ready;
 await delay(550);const report=await o.stop();
 const late=report.records.filter(r=>r.timingCategory==='observer_delayed');assert(late.length>=1);assert(late.some(r=>r.scheduleLagMs>100&&r.skippedSlots>=1));
 assert.equal((await s.stats()).maxActive,1);assert(report.records.length<8);
});

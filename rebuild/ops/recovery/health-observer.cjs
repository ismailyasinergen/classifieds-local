'use strict';
const {fork}=require('node:child_process');
const http=require('node:http');
const categories=[null,'timeout','connection_refused','connection_error','invalid_response','http_error','shutdown_cancelled'];
const defaults={targets:[{label:'original',port:8088},{label:'developer',port:8089}],intervalMs:10000,timeoutMs:5000,maxDurationMs:900000};
function configuration(input={}){
 const c={...defaults,...input};
 if(Object.keys(c).sort().join()!=='intervalMs,maxDurationMs,targets,timeoutMs'||
  !Array.isArray(c.targets)||c.targets.length<1||c.targets.length>2||
  new Set(c.targets.map(t=>t.label)).size!==c.targets.length||new Set(c.targets.map(t=>t.port)).size!==c.targets.length||
  !c.targets.every(t=>Object.keys(t).sort().join()==='label,port'&&['original','developer','synthetic'].includes(t.label)&&Number.isInteger(t.port)&&t.port>0&&t.port<65536)||
  !Number.isInteger(c.intervalMs)||c.intervalMs<20||c.intervalMs>10000||!Number.isInteger(c.timeoutMs)||c.timeoutMs<50||c.timeoutMs>5000||
  !Number.isInteger(c.maxDurationMs)||c.maxDurationMs<100||c.maxDurationMs>900000)throw Error('health_configuration_refused');
 return c;
}
function measure(target,timeoutMs,signal){
 return new Promise(resolve=>{
  let request,finished=false,httpStatus=null,bytes=0,chunks=[],timer;
  const finish=category=>{if(finished)return;finished=true;clearTimeout(timer);signal.removeEventListener('abort',cancel);request?.destroy();resolve({http:httpStatus,category});};
  const cancel=()=>finish('shutdown_cancelled');
  if(signal.aborted){cancel();return;}
  signal.addEventListener('abort',cancel,{once:true});
  timer=setTimeout(()=>finish('timeout'),timeoutMs);
  request=http.request({hostname:'127.0.0.1',port:target.port,path:'/health/',method:'GET',agent:false,maxHeaderSize:8192,headers:{Accept:'application/json'}},response=>{
   httpStatus=response.statusCode;
   if(httpStatus!==200){finish('http_error');return;}
   response.on('data',chunk=>{bytes+=chunk.length;if(bytes>1024){finish('invalid_response');return;}chunks.push(chunk);});
   response.on('error',()=>finish('connection_error'));
   response.on('end',()=>{try{const data=JSON.parse(Buffer.concat(chunks));finish(data?.status==='ok'?null:'invalid_response');}catch{finish('invalid_response');}chunks=[];});
  });
  request.on('error',error=>finish(error.code==='ECONNREFUSED'?'connection_refused':String(error.code).startsWith('HPE_')?'invalid_response':'connection_error'));
  request.end();
 });
}
async function worker(config){
 let stopping=false,reason='stop',sequence=0,completed=0;
 const abort=new AbortController(),wakes=new Set();
 const stop=why=>{if(stopping)return;stopping=true;reason=why;abort.abort();for(const wake of wakes)wake();};
 process.on('message',m=>{if(m?.type==='stop'&&Object.keys(m).length===1)stop('stop');else stop('protocol_error');});
 process.on('disconnect',()=>stop('parent_disconnected'));
 const send=m=>new Promise(resolve=>{if(!process.connected){stop('parent_disconnected');resolve();return;}process.send(m,error=>{if(error)stop('parent_disconnected');resolve();});});
 const wait=ms=>new Promise(resolve=>{const wake=()=>{clearTimeout(timer);wakes.delete(wake);resolve();};const timer=setTimeout(wake,Math.max(0,ms));wakes.add(wake);});
 const limit=setTimeout(()=>stop('duration_limit'),config.maxDurationMs);
 try{
  await Promise.all(config.targets.map(async target=>{
   let due=performance.now(),first=true;
   while(!stopping){
    if(sequence>=512){stop('sample_limit');break;}
    const start=performance.now(),record={id:++sequence,target:target.label,phase:first?'initial':'periodic',startedAt:new Date().toISOString(),startedMonoMs:start,scheduleLagMs:Math.max(0,start-due)};
    await send({type:'started',record});
    const outcome=await measure(target,config.timeoutMs,abort.signal),end=performance.now();
    let next=due+config.intervalMs;
    const skippedSlots=Math.max(0,Math.ceil((end-next)/config.intervalMs));next+=skippedSlots*config.intervalMs;
    const durationMs=end-start;
    await send({type:'sample',record:{...record,...outcome,endedAt:new Date().toISOString(),endedMonoMs:end,durationMs,skippedSlots,
     timingCategory:record.scheduleLagMs>100||durationMs>config.timeoutMs+100?'observer_delayed':'on_time'}});
    completed++;first=false;due=next;
    if(!stopping)await wait(due-performance.now());
   }
  }));
  await send({type:'done',started:sequence,completed,reason});
 }finally{clearTimeout(limit);if(process.connected)process.disconnect();}
}
function startHealthObservation(input){
 const config=configuration(input),env={};
 // Never inherit repository credentials, DB settings, NODE_OPTIONS or profile paths.
 for(const key of ['SystemRoot','WINDIR'])if(process.env[key])env[key]=process.env[key];
 const child=fork(__filename,['--health-worker'],{execArgv:[],env,cwd:__dirname,windowsHide:true,stdio:['ignore','ignore','ignore','ipc']});
 const pending=new Map(),initialTargets=new Set(),records=[];let sealed=false,stopping=false,done,problem=null,stopTimer,killTimer,readyResolved=false,resolveReady,resolveClosed;
 const ready=new Promise(r=>resolveReady=r),closed=new Promise(r=>resolveClosed=r);
 const finishReady=()=>{if(!readyResolved){readyResolved=true;resolveReady(records.filter(r=>r.phase==='initial').map(r=>Object.freeze({...r})));}};
 const fail=category=>{problem ||= category;if(child.exitCode===null)child.kill('SIGKILL');};
 const initialTimer=setTimeout(()=>fail('observer_start_timeout'),config.timeoutMs+2000);
 const exact=(o,keys)=>o&&Object.keys(o).sort().join()===keys.sort().join();
 const startKeys=['id','target','phase','startedAt','startedMonoMs','scheduleLagMs'];
 const finite=n=>Number.isFinite(n)&&n>=0;
 const timestamp=s=>typeof s==='string'&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(s)&&Number.isFinite(Date.parse(s));
 const validStart=r=>exact(r,startKeys)&&Number.isInteger(r.id)&&r.id>=1&&r.id<=512&&config.targets.some(t=>t.label===r.target)&&
  ['initial','periodic'].includes(r.phase)&&timestamp(r.startedAt)&&finite(r.startedMonoMs)&&finite(r.scheduleLagMs);
 child.on('message',m=>{
  if(sealed)return;
  if(m?.type==='started'&&exact(m,['type','record'])&&validStart(m.record)&&m.record.id===records.length+pending.size+1&&!pending.has(m.record.id)&&
   ![...pending.values()].some(r=>r.target===m.record.target)&&
   (m.record.phase==='initial'?!initialTargets.has(m.record.target):records.some(r=>r.phase==='initial'&&r.target===m.record.target))){
   if(m.record.phase==='initial')initialTargets.add(m.record.target);
   pending.set(m.record.id,m.record);return;
  }
  if(m?.type==='sample'&&exact(m,['type','record'])){
   const r=m.record,p=pending.get(r?.id);
   if(p&&exact(r,[...startKeys,'http','category','endedAt','endedMonoMs','durationMs','skippedSlots','timingCategory'])&&startKeys.every(k=>r[k]===p[k])&&
    (r.http===null||Number.isInteger(r.http)&&r.http>=100&&r.http<=599)&&categories.includes(r.category)&&(r.category!==null||r.http===200)&&
    timestamp(r.endedAt)&&finite(r.durationMs)&&finite(r.endedMonoMs)&&r.endedMonoMs>=r.startedMonoMs&&
    Math.abs(r.durationMs-(r.endedMonoMs-r.startedMonoMs))<0.01&&Number.isInteger(r.skippedSlots)&&r.skippedSlots>=0&&['on_time','observer_delayed'].includes(r.timingCategory)){
    pending.delete(r.id);records.push(r);
    if(records.filter(r=>r.phase==='initial').length===config.targets.length){clearTimeout(initialTimer);finishReady();}return;
   }
  }
  if(m?.type==='done'&&exact(m,['type','started','completed','reason'])&&m.started===records.length&&m.completed===records.length&&pending.size===0&&
   ['stop','duration_limit','sample_limit','parent_disconnected','protocol_error'].includes(m.reason)&&(m.reason!=='stop'||stopping)){done=m;return;}
  fail('observer_protocol_error');
 });
 function seal(code,signal){
  if(sealed)return;sealed=true;clearTimeout(initialTimer);clearTimeout(stopTimer);clearTimeout(killTimer);
  if(!done||code!==0)problem ||= 'observer_exit';
  if(done&&done.reason!=='stop')problem ||= 'observer_limit_or_protocol';
  const completedCount=records.length;
  // A dead process has no measured end time; never invent a completed measurement.
  for(const r of pending.values())records.push({...r,http:null,category:'observer_exit',endedAt:null,endedMonoMs:null,durationMs:null,skippedSlots:null,timingCategory:'unknown'});
  records.sort((a,b)=>a.id-b.id);finishReady();
  const report={status:problem?'incomplete':'complete',error:problem,environmentPolicy:'minimal_os_only',startedCount:records.length,completedCount,
   missingCompletions:pending.size,monitorExitCode:code,monitorSignal:signal||null,records:records.map(r=>Object.freeze({...r}))};
  Object.freeze(report.records);resolveClosed(Object.freeze(report));
 }
 child.on('error',()=>{problem='observer_spawn_failed';seal(null,null);});
 child.on('close',(code,signal)=>seal(code,signal));
 child.send({type:'start',config},error=>{if(error)fail('observer_start_failed');});
 return {pid:child.pid,ready,stop(){
  if(!stopping&&!sealed){stopping=true;clearTimeout(initialTimer);if(child.connected)child.send({type:'stop'},error=>{if(error)fail('observer_exit');});
   stopTimer=setTimeout(()=>{fail('observer_stop_timeout');killTimer=setTimeout(()=>seal(null,null),500);},2000);
  }return closed;
 }};
}
if(require.main===module){
 if(process.argv[2]!=='--health-worker'||!process.send)process.exitCode=1;
 else process.once('message',m=>{try{if(m?.type!=='start'||Object.keys(m).length!==2)throw Error();worker(configuration(m.config)).catch(()=>process.exit(1));}catch{process.exit(1);}});
}
module.exports={startHealthObservation,configuration};

'use strict';
const fs=require('node:fs'),path=require('node:path'),net=require('node:net');
const {execFileSync}=require('node:child_process');
const {developer,original,sourceAlias,compareMounts}=require('../inspect.cjs');
const baseline=require('../../../docs/phase15/baseline.json');
const services=['web','worker','scheduler','db','redis'];
const categories=['input_refused','identity_mismatch','source_mismatch','timeout','access_denied','command_failed','invalid_response','query_failed','worker_unresponsive','foreign_worker','health_failed','connection_refused','connection_error','http_error','not_measured'];
function check(ok,error){if(!ok)throw Error(error);}
function parseArgs(args){if(args.length===0)return 'developer';check(args.length===2&&args[0]==='--environment'&&['developer','original'].includes(args[1]),'input_refused');return args[1];}
const project=env=>env==='developer'?'classifieds-rebuild-dev':'classifieds-rebuild';
function validateRuntime(rows,environment){
 check(['developer','original'].includes(environment)&&Array.isArray(rows)&&rows.length===5,'identity_mismatch');
 const expected=baseline.runtime.filter(r=>r.project===project(environment));
 for(const service of services){
  const matches=rows.filter(r=>r.service===service),old=expected.find(r=>r.service===service);check(matches.length===1,'identity_mismatch');const r=matches[0];
  for(const key of ['id','image','project','configHash'])check(r[key]===old[key],'identity_mismatch');
  for(const key of ['volumes','networkIds','ports'])check(JSON.stringify(r[key])===JSON.stringify(old[key]),'identity_mismatch');
  try{compareMounts(r.mounts,old.mounts);}catch{throw Error('identity_mismatch');}
  check(r.state==='running'&&r.hostname===r.id.slice(0,12)&&net.isIP(r.ip)===4,'identity_mismatch');
  check(r.mounts.length===old.volumes.length+(['web','worker','scheduler'].includes(service)?1:0)&&r.mounts.every(m=>m.Type==='volume'&&old.volumes.includes(m.Name)||m.Type==='bind'&&m.Destination==='/app'),'identity_mismatch');
  if(['web','worker','scheduler'].includes(service)){
   const binds=r.mounts.filter(m=>m.Destination==='/app');
   check(binds.length===1&&binds[0].Type==='bind'&&binds[0].RW===false&&sourceAlias(binds[0].Source,(environment==='developer'?developer:original)+'/rebuild/backend'),'identity_mismatch');
  }
  if(service==='worker')check(JSON.stringify(r.cmd)===JSON.stringify(['celery','-A','config','worker','--loglevel=info','--concurrency=2']),'identity_mismatch');
  if(service==='scheduler')check(JSON.stringify(r.cmd)===JSON.stringify(['celery','-A','config','beat','--loglevel=info','--schedule=/var/lib/classifieds/celery/celerybeat-schedule']),'identity_mismatch');
 }
 check(new Set(rows.map(r=>r.ip)).size===5,'identity_mismatch');return rows;
}
function docker(args,input){
 try{return execFileSync('docker',args,{input,encoding:'utf8',timeout:12000,maxBuffer:65536,windowsHide:true,stdio:['pipe','pipe','pipe']});}
 catch(e){throw Error(e.code==='ETIMEDOUT'?'timeout':e.code==='EACCES'||e.code==='EPERM'||/access is denied|permission denied/i.test(String(e.stderr))?'access_denied':'command_failed');}
}
function inspect(environment){
 const format='{"id":{{json .Id}},"image":{{json .Image}},"hostname":{{json .Config.Hostname}},"cmd":{{json .Config.Cmd}},"project":{{json (index .Config.Labels "com.docker.compose.project")}},"service":{{json (index .Config.Labels "com.docker.compose.service")}},"configHash":{{json (index .Config.Labels "com.docker.compose.config-hash")}},"state":{{json .State.Status}},"mounts":{{json .Mounts}},"portsRaw":{{json .NetworkSettings.Ports}},"networks":{{json .NetworkSettings.Networks}}}';
 try{return docker(['inspect','--format',format,...services.map(s=>project(environment)+'-'+s+'-1')]).trim().split(/\r?\n/).map(line=>{
  const r=JSON.parse(line),nets=Object.values(r.networks);return {...r,networkIds:nets.map(n=>n.NetworkID),ip:nets.length===1?nets[0].IPAddress:null,
   volumes:r.mounts.filter(m=>m.Type==='volume').map(m=>m.Name).sort(),ports:Object.values(r.portsRaw||{}).flatMap(p=>p||[]).map(p=>({host:p.HostIp,port:p.HostPort}))};
 });}catch(e){if(categories.includes(e.message))throw e;throw Error('invalid_response');}
}
function exact(data,keys){return data&&typeof data==='object'&&!Array.isArray(data)&&Object.keys(data).sort().join()===keys.sort().join();}
const count=n=>Number.isSafeInteger(n)&&n>=0;
const age=n=>typeof n==='number'&&Number.isFinite(n)&&n>=0;
function validateProbe(data,mode){
 let valid=false;
 if(mode==='outbox')valid=exact(data,['sourceUnprocessed','oldestAgeSeconds','consumer','consumption'])&&count(data.sourceUnprocessed)&&data.consumer==='saved_search_in_app_v1'&&exact(data.consumption,['pending','retry','completed','skipped','failed'])&&Object.values(data.consumption).every(count)&&(data.sourceUnprocessed===0?data.oldestAgeSeconds===null:age(data.oldestAgeSeconds));
 if(mode==='media')valid=exact(data,['pending','ready','failed','attemptLimitReached','oldestPendingAgeSeconds'])&&['pending','ready','failed','attemptLimitReached'].every(k=>count(data[k]))&&data.attemptLimitReached<=data.pending+data.ready+data.failed&&(data.pending===0?data.oldestPendingAgeSeconds===null:age(data.oldestPendingAgeSeconds));
 if(mode==='worker')valid=exact(data,['responding'])&&data.responding===true;
 if(mode==='health')valid=exact(data,['http','status'])&&data.http===200&&data.status==='ok';
 check(valid,'invalid_response');return data;
}
function probe(mode,rows){
 check(['outbox','media','worker'].includes(mode),'input_refused');
 const get=s=>rows.find(r=>r.service===s);
 const code=fs.readFileSync(path.join(__dirname,'probe.py'),'utf8');
 const raw=docker(['exec','-i',get('web').id,'python','-B','-c',code,mode,get('db').ip,get('redis').ip,'celery@'+get('worker').hostname]);
 let result;try{result=JSON.parse(raw);}catch{throw Error('invalid_response');}
 if(exact(result,['ok','error'])&&result.ok===false&&categories.includes(result.error))throw Error(result.error);
 check(exact(result,['ok','data'])&&result.ok===true,'invalid_response');return validateProbe(result.data,mode);
}
async function measure(action){const startedAt=new Date().toISOString(),start=performance.now();let result;
 try{result={status:'measured',error:null,data:await action()};}catch(e){result={status:'unavailable',error:categories.includes(e.message)?e.message:'command_failed',data:null};}
 return {startedAt,endedAt:new Date().toISOString(),durationMs:performance.now()-start,...result};
}
async function collect(environment,adapter={inspect,probe,health}){
 let rows;const runtime=await measure(()=>{rows=validateRuntime(adapter.inspect(environment),environment);return {services:rows.map(r=>({service:r.service,running:true,identityVerified:true,sourceAndImageVerified:true})),functionalHealthInferred:false};});
 const sections={runtime};
 const available=runtime.status==='measured';
 for(const mode of ['worker','outbox','media'])sections[mode]=await measure(()=>{check(available,'not_measured');return validateProbe(adapter.probe(mode,rows),mode);});
 sections.scheduler=await measure(()=>{check(available,'not_measured');return {processRunning:true,dispatchEvidence:'unavailable',reason:'no_reliable_dispatch_heartbeat'};});
 if(sections.scheduler.status==='measured')sections.scheduler.status='unknown';
 sections.health=await measure(async()=>{check(available,'not_measured');return validateProbe(await adapter.health(environment),'health');});
 return {environment,sections,brokerControlSideEffect:'targeted_ping_and_ephemeral_reply_queue_no_business_task',operationalThresholds:'not_defined',applicationWritesPerformed:false};
}
async function health(environment){
 const {startHealthObservation}=require('../../recovery/health-observer.cjs');
 const observer=startHealthObservation({targets:[{label:environment,port:environment==='developer'?8089:8088}],maxDurationMs:10000});
 try{const initial=await observer.ready;check(initial.length===1,'health_failed');check(initial[0].http===200&&initial[0].category===null,categories.includes(initial[0].category)?initial[0].category:'health_failed');return {http:200,status:'ok'};}
 finally{const closed=await observer.stop();check(closed.status==='complete','health_failed');}
}
function summary(report){
 const s=report.sections,lines=['# İşletim gözlemi — '+report.environment,'', 'Koşu: '+report.runId,''];
 const names={runtime:'Servis kimlikleri',worker:'Worker yanıtı',scheduler:'Zamanlayıcı',outbox:'Outbox birikimi',media:'Medya işleme',health:'Web sağlığı',protection:'Son koruma'};
 for(const [name,r] of Object.entries(s))lines.push(names[name]+': '+r.status+'; hata: '+(r.error||'yok')+'; '+r.startedAt+'; süre '+r.durationMs.toFixed(1)+' ms'+(r.data?' — '+JSON.stringify(r.data):''));
 if(s.outbox.status==='measured'&&s.outbox.data){const d=s.outbox.data;lines.push('Kaynak outbox işlenmemiş: '+d.sourceUnprocessed+'; en eski yaş (saniye): '+(d.oldestAgeSeconds??'kayıt yok'),'Tüketici '+d.consumer+': '+['pending','retry','completed','skipped','failed'].map(k=>k+': '+d.consumption[k]).join('; '));}
 else lines.push('Tüketici durumu ölçülemedi (unavailable); sıfır veya tüketici yokluğu olarak yorumlanmaz.');
 if(s.media.data)lines.push('Görseller: bekleyen '+s.media.data.pending+', hazır '+s.media.data.ready+', başarısız '+s.media.data.failed+', deneme sınırında '+s.media.data.attemptLimitReached+'; en eski bekleyen yaş (saniye): '+s.media.data.oldestPendingAgeSeconds);
 lines.push('','Scheduler süreç durumu iş gönderimi kanıtı değildir. Kaynak outbox sayısı tüketiciye özel ilerleme değildir; birikim tek başına arıza sayılmaz.','Worker ping broker kontrol mesajı ve geçici yanıt kuyruğu üretir; iş görevi yayımlanmaz. Yaş/sayı hedefleri belirlenmemiştir.');return lines.join('\n')+'\n';
}
module.exports={parseArgs,validateRuntime,validateProbe,inspect,probe,collect,measure,summary,project,docker};

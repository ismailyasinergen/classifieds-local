'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {safeResources}=require('../lifecycle.cjs');
const {execFileSync}=require('node:child_process');
const {requireSafe,guardReader,normalize,output,errors,directoryOutput}=require('./contract.cjs');
const {verifySources}=require('../inspect.cjs');
const {inspect,validateRuntime,project}=require('../observability/core.cjs');
const baseline=require('../../../docs/phase15/baseline.json');
const format='{"id":{{json .Id}},"image":{{json .Image}},"run":{{json (index .Config.Labels "phase9.run")}},"nonce":{{json (index .Config.Labels "phase15.attempt")}},"user":{{json .Config.User}},"mounts":{{json .Mounts}},"network":{{json .HostConfig.NetworkMode}},"ports":{{json .HostConfig.PortBindings}},"readonly":{{json .HostConfig.ReadonlyRootfs}},"privileged":{{json .HostConfig.Privileged}},"capAdd":{{json .HostConfig.CapAdd}},"capDrop":{{json .HostConfig.CapDrop}},"security":{{json .HostConfig.SecurityOpt}},"pid":{{json .HostConfig.PidMode}},"userns":{{json .HostConfig.UsernsMode}},"ipc":{{json .HostConfig.IpcMode}}}';
function docker(args,{input,timeout=12000}={}){
 try{return execFileSync('docker',args,{input,encoding:'utf8',timeout,maxBuffer:32*1024*1024,windowsHide:true,stdio:['pipe','pipe','pipe']}).trim();}
 catch(e){throw Error(e.code==='ETIMEDOUT'?'timeout':/permission denied|access is denied/i.test(String(e.stderr))?'access_denied':'command_failed');}
}
function unpack(raw,field){let r;try{r=JSON.parse(raw);}catch{throw Error('invalid_response');}if(r?.ok===false&&errors.includes(r.error))throw Error(r.error);requireSafe(r?.ok===true&&Object.keys(r).sort().join()===['ok',field].sort().join(),'invalid_response');if(field==='assets')requireSafe(Array.isArray(r.assets)&&r.assets.length<=10000&&r.assets.every(a=>Number.isSafeInteger(a.id)&&a.id>0),'invalid_response');return r[field];}
const ownerCode="import os,stat,json\nr=[]\nfor p in ['/var/lib/classifieds/media']:\n s=os.lstat(p);r.append([s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode),stat.S_ISDIR(s.st_mode)])\nprint(json.dumps({'uid':os.getuid(),'gid':os.getgid(),'uidMap':open('/proc/self/uid_map').read().split(),'gidMap':open('/proc/self/gid_map').read().split(),'directories':r}))";
function guardOwner(m){requireSafe(m.uid===0&&m.gid===0&&['uidMap','gidMap'].every(k=>JSON.stringify(m[k])==='["0","0","4294967295"]')&&JSON.stringify(m.directories)==='[[0,0,493,true]]','reader_preflight_refused');}
function makeAdapter(environment,run){
 requireSafe(['developer','original'].includes(environment)&&/^[a-f0-9]{24}$/.test(run),'input_refused');
 const end=performance.now()+60000;let rows,receipt,attempted=false,removed=false,unknown=false,before=[];const nonce=crypto.randomBytes(16).toString('hex');
 const resources=()=>safeResources({run,role:'media-reader',known:receipt?.id?[receipt.id]:[],removed:removed?[receipt.id]:[],retained:receipt?.id&&!removed?[receipt.id]:[],unknown,status:unknown||attempted&&!removed?'cleanup_blocked':removed?'removed':'not_created',persistence:'not_attempted'});
 function close(){
  if(removed||!attempted)return removed?'removed_exact_owned':'not_created';
  try{requireSafe(receipt?.id&&!unknown,'cleanup_blocked');readerInspect();require('../graceful.cjs').gracefulStop(docker,receipt.id);docker(['rm',receipt.id]);removed=true;return 'removed_exact_owned';}
  catch{throw Object.assign(Error('cleanup_blocked'),{resources:resources()});}
 }
 function discover(){
  unknown=true;
  try{const ids=docker(['ps','-aq','--no-trunc','--filter','label=phase15.attempt='+nonce]).split(/\r?\n/).filter(Boolean);requireSafe(ids.length===1,'cleanup_blocked');receipt.id=ids[0];readerInspect();unknown=false;}catch{}
 }
 function call(args,input){const remaining=Math.floor(end-performance.now());requireSafe(remaining>0,'timeout');return docker(args,{input,timeout:Math.min(24000,remaining)});}
 const readerInspect=()=>{requireSafe(receipt&&/^[a-f0-9]{64}$/.test(receipt.id),'identity_mismatch');const m=JSON.parse(docker(['inspect','--format',format,receipt.id]));guardReader(m,receipt);requireSafe(m.nonce===nonce&&!before.includes(m.id)&&!baseline.containerIds.includes(m.id),'identity_mismatch');};
 const preflight=()=>{readerInspect();const r=JSON.parse(call(['exec',receipt.id,'python','-B','/ops/preflight.py']));directoryOutput(r.directories);if(r.metadataAccessVerified!==true){const e=Error('reader_preflight_refused');e.directories=r.directories;throw e;}return r.directories;};
 return {
  verify(){require('../gate.cjs').verifyAcceptance();verifySources();const current=validateRuntime(inspect(environment),environment);const norm=xs=>xs.map(r=>({...r,mounts:[...r.mounts].sort((a,b)=>a.Destination.localeCompare(b.Destination))}));if(rows)requireSafe(JSON.stringify(norm(rows))===JSON.stringify(norm(current)),'identity_mismatch');rows=current;requireSafe(performance.now()<end,'timeout');},
  open(){
   try {
   const app=rows.find(r=>r.service==='web'),volume=project(environment)+'_rebuild_media';
   requireSafe(app.mounts.some(m=>m.Type==='volume'&&m.Name===volume&&m.Destination==='/var/lib/classifieds/media'),'identity_mismatch');
   const old=baseline.volumes.find(v=>v.name===volume);
   const v=JSON.parse(call(['volume','inspect','--format','{"name":{{json .Name}},"createdAt":{{json .CreatedAt}},"driver":{{json .Driver}},"scope":{{json .Scope}}}',volume]));requireSafe(JSON.stringify(v)===JSON.stringify(old),'identity_mismatch');
   guardOwner(JSON.parse(call(['exec',app.id,'python','-B','-c',ownerCode])));
   receipt={run,environment,volume,image:app.image};
   before=docker(['ps','-aq','--no-trunc']).split(/\r?\n/).filter(Boolean);attempted=true;
   receipt.id=call(['create','--pull','never','--name','phase9-reader-'+run,'--label','phase9.run='+run,'--label','phase15.attempt='+nonce,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user','0:0','--mount','type=volume,source='+volume+',target=/media,readonly','--mount','type=bind,source='+__dirname+',target=/ops,readonly',app.image,'python','-B','-c',"import signal,sys,time; signal.signal(signal.SIGTERM,lambda *_:sys.exit(0)); time.sleep(90)"]);
   readerInspect();call(['start',receipt.id]);return preflight();
   }catch(error){if(attempted&&!receipt?.id)discover();try{close();}catch{}throw Object.assign(Error(errors.includes(error.message)?error.message:'command_failed'),{resources:resources(),ownershipReleased:true,directories:error.directories});}
  },
  snapshot(){const code=fs.readFileSync(path.join(__dirname,'snapshot.py'),'utf8');return unpack(call(['exec',rows.find(r=>r.service==='web').id,'python','-B','-c',code,rows.find(r=>r.service==='db').ip]),'assets');},
  scan(){preflight();return unpack(call(['exec',receipt.id,'python','-B','/ops/helper.py','scan',environment]),'data');},
  compare(data){return output(unpack(call(['exec','-i',receipt.id,'python','-B','/ops/helper.py','compare',environment],JSON.stringify(data)),'data'),environment);},
  close,
  resources,
 };
}
module.exports={makeAdapter,guardOwner,docker,format,unpack};

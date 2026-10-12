'use strict';
// Two fixed commands only; daemon ownership is independent of the private stream client.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {command,image,developer,docs,sourceAlias}=require('./inspect.cjs');
const {persist,mustPersist,failure}=require('./lifecycle.cjs');
const {gracefulStop}=require('./graceful.cjs');
const docker=args=>command('docker',args),check=ok=>{if(!ok)throw Error('helper_identity_refused');};
const dnsCode="import socket,json; print(json.dumps(sorted({r[4][0] for r in socket.getaddrinfo('host.docker.internal',8088,type=socket.SOCK_STREAM)})))";
const format='{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},"labels":{{json .Config.Labels}},"entrypoint":{{json .Config.Entrypoint}},"cmd":{{json .Config.Cmd}},"user":{{json .Config.User}},"stdin":{{json .Config.OpenStdin}},"tty":{{json .Config.Tty}},"mounts":{{json .Mounts}},"network":{{json .HostConfig.NetworkMode}},"networks":{{json .NetworkSettings.Networks}},"ports":{{json .HostConfig.PortBindings}},"readonly":{{json .HostConfig.ReadonlyRootfs}},"privileged":{{json .HostConfig.Privileged}},"capAdd":{{json .HostConfig.CapAdd}},"capDrop":{{json .HostConfig.CapDrop}},"security":{{json .HostConfig.SecurityOpt}},"pid":{{json .HostConfig.PidMode}},"userns":{{json .HostConfig.UsernsMode}},"ipc":{{json .HostConfig.IpcMode}},"autoRemove":{{json .HostConfig.AutoRemove}},"logDriver":{{json .HostConfig.LogConfig.Type}},"state":{{json .State.Status}},"exit":{{json .State.ExitCode}}}';
function createHelper(role,run){
 check(['archive','dns'].includes(role)&&/^[a-f0-9]{16}$/.test(run));
 const attempt=crypto.randomBytes(16).toString('hex'),name=`phase15-${role}-${run}-${attempt}`;
 const file=path.join(docs,`helper-${attempt}.json`),record={run,attempt,role,name,phase:'preparing',creation:'not_requested',execution:'not_started',resources:{run,role,known:[],removed:[],retained:[],unknown:false,status:'not_created',persistence:'not_attempted'}};
 const r=record.resources;let id,before=[],attempted=false,closed=false,createdFile=false,networkId;
 const args=role==='archive'?['-B','/ops/archive_io.py']:['-B','-c',dnsCode];
 const inspect=()=>{
  check(/^[a-f0-9]{64}$/.test(id)&&!before.includes(id));
  const m=JSON.parse(docker(['inspect','--format',format,id]));
  check(m.id===id&&m.name==='/'+name&&m.image===image&&m.labels?.['phase15.run']===run&&m.labels['phase15.attempt']===attempt&&m.labels['phase15.role']===role);
  check(JSON.stringify(m.entrypoint)==='["python"]'&&JSON.stringify(m.cmd)===JSON.stringify(args)&&m.user==='1000:1000'&&m.stdin===true&&m.tty===false);
  check(m.readonly===true&&m.privileged===false&&!(m.capAdd||[]).length&&JSON.stringify(m.capDrop)==='["ALL"]'&&JSON.stringify(m.security)==='["no-new-privileges"]'&&!Object.keys(m.ports||{}).length);
  check(m.pid===''&&m.userns===''&&m.ipc==='private'&&m.autoRemove===false&&m.logDriver==='none');
  check(m.network===(role==='archive'?'none':'bridge'));
  const nets=Object.entries(m.networks||{});check(nets.length===1&&nets[0][0]===(role==='archive'?'none':'bridge')&&(!nets[0][1].NetworkID||nets[0][1].NetworkID===networkId));
  const mounts=m.mounts||[];check(mounts.length===(role==='archive'?2:0));
  if(role==='archive')for(const [destination,source] of [['/ops',__dirname],['/source',developer]])check(mounts.filter(m=>m.Type==='bind'&&!m.RW&&m.Destination===destination&&sourceAlias(m.Source,source)).length===1);
  return m;
 };
 const save=()=>{r.persistence=createdFile?persist(fs,file,record):'write_failed';return r.persistence;};
 const finish=()=>{
  if(!closed){closed=true;
   if(id)try{inspect();gracefulStop(docker,id);const last=inspect();check(['created','exited'].includes(last.state));record.daemonExit=last.state==='exited'?last.exit:null;record.daemonState=last.state;docker(['rm',id]);r.removed.push(id);
    const all=docker(['ps','-aq','--no-trunc']).split(/\r?\n/);if(all.includes(id))throw Error('cleanup_blocked');record.absenceVerified=true;
   }catch{r.unknown=true;}
   r.retained=r.known.filter(x=>!r.removed.includes(x));r.status=r.unknown||r.retained.length?'cleanup_blocked':attempted?'removed':'not_created';record.phase='closed';save();
  }
  if(r.status==='cleanup_blocked'||r.persistence==='write_failed')throw Object.assign(failure(Error(r.status==='cleanup_blocked'?'cleanup_blocked':'receipt_write_failed'),'cleanup_blocked'),{resourceGroups:{[role]:r},helperOutcomes:{[role]:{run,attempt,phase:record.phase,creation:record.creation,execution:record.execution,daemonState:record.daemonState||'unknown',daemonExit:record.daemonExit??null,absenceVerified:record.absenceVerified===true}}});
  return {resourceGroups:{[role]:structuredClone(r)},helperOutcomes:{[role]:{run,attempt,phase:record.phase,creation:record.creation,execution:record.execution,daemonState:record.daemonState||'unknown',daemonExit:record.daemonExit??null,absenceVerified:record.absenceVerified===true}}};
 };
 try{
  mustPersist(fs,file,record,true);createdFile=true;
  before=docker(['ps','-aq','--no-trunc']).split(/\r?\n/).filter(Boolean);
  const baseline=JSON.parse(fs.readFileSync(path.join(docs,'baseline.json')));before=[...new Set([...before,...baseline.containerIds])];
  const net=JSON.parse(docker(['network','inspect','--format','{"id":{{json .Id}},"name":{{json .Name}},"driver":{{json .Driver}}}',role==='archive'?'none':'bridge']));
  check(/^[a-f0-9]{64}$/.test(net.id)&&net.name===(role==='archive'?'none':'bridge')&&net.driver===(role==='archive'?'null':'bridge'));networkId=net.id;
  check(!docker(['ps','-aq','--no-trunc','--filter',`name=^/${name}$`]));
  record.phase='create_requested';record.creation='requested_unconfirmed';mustPersist(fs,file,record);
  const create=['create','--pull','never','--name',name,'--label',`phase15.run=${run}`,'--label',`phase15.attempt=${attempt}`,'--label',`phase15.role=${role}`,'--network',role==='archive'?'none':'bridge','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user','1000:1000','--log-driver','none','--entrypoint','python','-i'];
  if(role==='archive')create.push('--mount',`type=bind,source=${__dirname},target=/ops,readonly`,'--mount',`type=bind,source=${developer},target=/source,readonly`);
  attempted=true;id=docker([...create,image,...args]);check(/^[a-f0-9]{64}$/.test(id));r.known=[id];record.phase='created';
  inspect();record.creation='confirmed';mustPersist(fs,file,record);
 }catch(error){
  if(attempted&&!/^[a-f0-9]{64}$/.test(id||'')){id=undefined;r.unknown=true;
   try{const found=docker(['ps','-aq','--no-trunc','--filter',`label=phase15.attempt=${attempt}`]).split(/\r?\n/).filter(Boolean);check(found.length<=1);if(found.length){id=found[0];r.known=[id];inspect();record.creation='confirmed';r.unknown=false;}}catch{}
  }
  const primary=failure(error,'helper_create_failed');let outcome;try{outcome=finish();}catch(e){outcome=e;}throw Object.assign(primary,{resourceGroups:outcome.resourceGroups||{[role]:r},helperOutcomes:outcome.helperOutcomes});
 }
 return {run,attempt,id,role,
  producer(input){check(!closed);inspect();record.phase='start_requested';record.execution='requested';mustPersist(fs,file,record);return {command:'docker',args:['start','--attach','--interactive',id],input};},
  verifyExit(){const m=inspect();record.daemonExit=m.exit;check(m.state==='exited'&&m.exit===0);record.phase='exited';record.execution='exit_verified';mustPersist(fs,file,record);},
  close:finish};
}
async function backupArchive(repo,files,context){
 let helper,primary,result;const outcome={};
 try{helper=createHelper('archive',context.run);result=await require('../recovery/repository.cjs').backupComponent(repo,'source.tar',helper.producer(Buffer.from(JSON.stringify(files))),context);helper.verifyExit();}
 catch(e){primary=failure(e,'capture_failed');require('./lifecycle.cjs').mergeLifecycle(outcome,e);}
 finally{if(helper)try{Object.assign(outcome,helper.close());}catch(e){require('./lifecycle.cjs').mergeLifecycle(outcome,e);primary ||= failure(e,'cleanup_blocked');}}
 if(primary)throw Object.assign(primary,outcome);return {component:result,...outcome};
}
function resolveHost(run){
 let helper,primary,hosts;const outcome={};
 try{helper=createHelper('dns',run);const s=helper.producer();let bytes;try{bytes=require('node:child_process').execFileSync(s.command,s.args,{windowsHide:true,stdio:['ignore','pipe','pipe'],timeout:15000,maxBuffer:4096});}catch{throw Error('command_failed');}helper.verifyExit();hosts=JSON.parse(bytes);check(Array.isArray(hosts)&&hosts.length>0&&hosts.length<=16&&hosts.every(h=>require('node:net').isIP(h)));}
 catch(e){primary=failure(e,'operation_failed');require('./lifecycle.cjs').mergeLifecycle(outcome,e);}
 finally{if(helper)try{Object.assign(outcome,helper.close());}catch(e){require('./lifecycle.cjs').mergeLifecycle(outcome,e);primary ||= failure(e,'cleanup_blocked');}}
 if(primary)throw Object.assign(primary,outcome);return {hosts,...outcome};
}
module.exports={createHelper,backupArchive,resolveHost,format};

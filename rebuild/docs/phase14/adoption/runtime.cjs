'use strict';
const cp=require('node:child_process');
const {DEV,ORIGINAL,IMAGE,OLD}=require('./preflight.cjs');
const wait=ms=>new Promise(r=>setTimeout(r,ms));
function docker(args,{cwd=DEV,input,timeout=30000}={}){const r=cp.spawnSync('docker',args,{cwd,input,encoding:'utf8',timeout,maxBuffer:20*1024*1024,windowsHide:true});if(r.status!==0){const e=Error('docker_command_failed');e.detail={nativeExit:r.status,category:r.error?'process_timeout_or_start_error':'docker_nonzero',processCode:['E2BIG','ENAMETOOLONG','EINVAL','ETIMEDOUT','ENOENT','EACCES'].includes(r.error?.code)?r.error.code:null};throw e;}return r.stdout.trim();}
const compose=(environment)=>{if(!['original','developer'].includes(environment))throw Error('environment_refused');return ['compose','-f','rebuild/compose.yaml','-f',environment==='original'?'rebuild/compose.original-notifications.yaml':'rebuild/compose.dev.yaml','-p',environment==='original'?'classifieds-rebuild':'classifieds-rebuild-dev'];};
const norm=x=>x.replaceAll('\\','/').toLowerCase().replace('/run/desktop/mnt/host/c/','c:/').replace('/host_mnt/c/','c:/');
const format='{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},"labels":{{json .Config.Labels}},"state":{{json .State.Status}},"exit":{{json .State.ExitCode}},"mounts":{{json .Mounts}},"ports":{{json .HostConfig.PortBindings}},"networkMode":{{json .HostConfig.NetworkMode}},"networks":{{json .NetworkSettings.Networks}},"privileged":{{json .HostConfig.Privileged}},"pidMode":{{json .HostConfig.PidMode}},"userns":{{json .HostConfig.UsernsMode}},"readonly":{{json .HostConfig.ReadonlyRootfs}},"caps":{{json .HostConfig.CapAdd}},"capDrop":{{json .HostConfig.CapDrop}},"security":{{json .HostConfig.SecurityOpt}},"flag":"{{range .Config.Env}}{{if eq . "IN_APP_NOTIFICATIONS_ENABLED=1"}}enabled{{end}}{{end}}"}';
function inspect(id){return JSON.parse(docker(['inspect','--format',format,id]));}
function inventory(expectedOriginal=OLD){const rows=[];for(const environment of ['original','developer'])for(const service of ['web','worker','scheduler','db','redis']){
 const project=environment==='original'?'classifieds-rebuild':'classifieds-rebuild-dev',r=inspect(project+'-'+service+'-1'),app=['web','worker','scheduler'].includes(service);
 if(r.labels['com.docker.compose.project']!==project||r.labels['com.docker.compose.service']!==service||r.state!=='running'||r.privileged||r.pidMode==='host'||r.userns==='host')throw Error('runtime_identity_refused');
 if(app){const bind=r.mounts.filter(m=>m.Destination==='/app');if(r.image!==(environment==='original'?expectedOriginal:IMAGE)||bind.length!==1||bind[0].RW||norm(bind[0].Source)!==norm((environment==='original'?ORIGINAL:DEV)+'/rebuild/backend')||r.flag!=='enabled')throw Error('application_identity_refused');}
 const ports=Object.values(r.ports||{}).flat();if(ports.some(p=>p.HostIp!=='127.0.0.1'))throw Error('port_refused');if(service==='web'&&(ports.length!==1||ports[0].HostPort!==(environment==='original'?'8088':'8089')))throw Error('web_port_refused');
 rows.push({environment,service,id:r.id,image:r.image,configHash:r.labels['com.docker.compose.config-hash'],mounts:r.mounts,networks:r.networks,ports:r.ports,flag:r.flag});
 }return rows;}
function validateOwned(r,s){
 if(!/^[a-f0-9]{64}$/.test(r.id)||r.name!=='/'+s.name||r.image!==IMAGE||r.labels['phase14.adoption.run']!==s.run||s.baseline.includes(r.id)||r.privileged||r.pidMode==='host'||r.userns==='host'||Object.values(r.ports||{}).flat().length)throw Error('temporary_identity_refused');
 if(s.kind==='probe'){if(r.networkMode!=='none'||r.mounts.length||!r.readonly||r.caps?.length||!r.capDrop?.includes('ALL')||!r.security?.includes('no-new-privileges'))throw Error('temporary_isolation_refused');}
 else if(s.kind==='migration'){
 if(r.labels['com.docker.compose.project']!=='classifieds-rebuild'||r.labels['com.docker.compose.service']!=='web'||r.labels['com.docker.compose.oneoff']!=='True')throw Error('temporary_project_refused');
 const mounts=r.mounts.map(m=>({type:m.Type,source:m.Type==='bind'?norm(m.Source):m.Name,target:m.Destination,rw:m.RW}));
 if(JSON.stringify(mounts.sort((a,b)=>a.target.localeCompare(b.target)))!==JSON.stringify(s.mounts))throw Error('temporary_mount_refused');
 if(Object.values(r.networks).map(n=>n.NetworkID).sort().join()!==s.networks.join())throw Error('temporary_network_refused');
 }else throw Error('temporary_kind_refused');return r;
}
async function oneShot(s,create,receipt,api={inspect,docker,wait}){
 const result={name:s.name,run:s.run,id:null,primary:null,nativeExit:null,cleanup:{removed:false,retained:[],unknown:false},persistence:true};let attempted=false,removed=false;
 const record=()=>{try{receipt(result);}catch{result.persistence=false;throw Error('receipt_failed');}};
 try{record();attempted=true;const id=create().trim();if(!/^[a-f0-9]{64}$/.test(id))throw Error('create_response_invalid');result.id=id;validateOwned(api.inspect(id),s);record();
 const deadline=Date.now()+(s.timeoutMs||90000);while(true){const r=validateOwned(api.inspect(id),s);if(r.state==='exited'){result.nativeExit=r.exit;break;}if(Date.now()>=deadline)throw Error('temporary_exit_timeout');await api.wait(250);}
 if(result.nativeExit!==0)throw Error('temporary_command_nonzero');if(s.collect)result.output=s.collect(result.id);
 }catch(e){result.primary=e.message&&/^[a-z_]+$/.test(e.message)?e.message:'temporary_operation_failed';if(e.detail)result.commandFailure=e.detail;}
 finally{
 if(attempted){try{
 if(!result.id){const found=api.inspect(s.name);validateOwned(found,s);result.id=found.id;}
 const r=validateOwned(api.inspect(result.id),s);
 if(r.state==='exited'&&result.nativeExit===null){result.nativeExit=r.exit;if(r.exit===0&&s.collect){try{result.output=s.collect(r.id);}catch{result.outputError='output_unverified';}}}
 if(r.state!=='exited'&&r.state!=='created'){result.cleanup.retained=[r.id];}
 else{api.docker(['rm',r.id]);removed=true;result.cleanup.removed=true;const ids=api.docker(['ps','-a','--no-trunc','--format','{{.ID}}']).split(/\r?\n/);if(ids.includes(r.id))throw Error('removal_unconfirmed');}
 }catch{result.cleanup.unknown=!result.id;if(!removed&&result.id)result.cleanup.retained=[result.id];result.cleanup.category='cleanup_blocked';}}
 try{record();}catch{if(!result.primary)result.primary='receipt_failed';}
 }
 result.ok=!result.primary&&result.nativeExit===0&&result.cleanup.removed&&!result.cleanup.category&&result.persistence;
 return result;
}
function safeExitedSuccess(r,s,read=inspect){return r.nativeExit===0&&r.output?.nativeSuccess===true&&!r.cleanup.unknown&&(r.cleanup.removed||validateOwned(read(r.id),s).state==='exited');}
module.exports={docker,compose,inspect,inventory,validateOwned,oneShot,wait,norm,safeExitedSuccess};

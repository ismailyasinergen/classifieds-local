'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const {command,image,manifest,developer,sourceAlias}=require('./inspect.cjs');
const {requireSafe}=require('../recovery/guards.cjs');
const {persist,mustPersist,failure,safeResources}=require('./lifecycle.cjs');
const owners=new WeakMap();
const docs=path.join(developer,'rebuild/docs/phase15');
const docker=args=>command('docker',args);
const imageRefs={web:image,db:'postgres:17.11-bookworm@sha256:3645570cccdfa447589da9f57dd740faa29b30938e861289a5574b6ca6b03826',redis:'redis:7.4.11-bookworm@sha256:4fa24486b8bcca8eec45ee0eb166edc674795e53a2b53d1a9ef263eecebaac85'};
const metadata=id=>JSON.parse(docker(['inspect','--format','{"id":{{json .Id}},"image":{{json .Image}},"labels":{{json .Config.Labels}},"mounts":{{json .Mounts}},"ports":{{json .HostConfig.PortBindings}},"networks":{{json .NetworkSettings.Networks}},"privileged":{{json .HostConfig.Privileged}},"capAdd":{{json .HostConfig.CapAdd}},"readonly":{{json .HostConfig.ReadonlyRootfs}},"state":{{json .State.Status}}}',id]));
function validateOwned(receipt) {
  requireSafe(/^[a-f0-9]{16}$/.test(receipt.run)&&['synthetic-source','synthetic-target','original-target'].includes(receipt.role));
  requireSafe(receipt.project===`classifieds-rebuild-recovery-${receipt.run}-${receipt.role}`);
  requireSafe(Object.keys(receipt.services).sort().join(',')==='db,redis,web');
  const baseline=JSON.parse(fs.readFileSync(path.join(docs,'baseline.json')));
  for(const [service,id] of Object.entries(receipt.services)) {
    requireSafe(/^[a-f0-9]{64}$/.test(id)&&!baseline.containerIds.includes(id));
    const m=metadata(id);
    const security=JSON.parse(docker(['inspect','--format','{"imageRef":{{json .Config.Image}},"capDrop":{{json .HostConfig.CapDrop}},"securityOpt":{{json .HostConfig.SecurityOpt}},"tmpfs":{{json .HostConfig.Tmpfs}}}',id]));
    requireSafe(security.imageRef===imageRefs[service]&&security.capDrop?.includes('ALL')&&security.securityOpt?.some(s=>s==='no-new-privileges:true'||s==='no-new-privileges'));
    if(service==='web')requireSafe(docker(['inspect','--format','{{range .Config.Env}}{{if eq . "IN_APP_NOTIFICATIONS_ENABLED=0"}}disabled{{end}}{{end}}',id])==='disabled','runtime_validation_failed');
    requireSafe(m.labels['com.docker.compose.project']===receipt.project&&m.labels['com.docker.compose.service']===service);
    requireSafe(m.image===receipt.images[service]&&(service!=='web'||m.image===image));
    requireSafe(m.readonly&&!m.privileged&&!(m.capAdd||[]).length&&!Object.keys(m.ports||{}).length);
    requireSafe(Object.values(m.networks).length===1&&Object.values(m.networks)[0].NetworkID===receipt.networkId&&!baseline.networkIds.includes(receipt.networkId));
    const destinations={web:['/var/lib/classifieds/media','/run','/tmp'],db:['/var/lib/postgresql/data','/var/run/postgresql','/tmp'],redis:['/data']}[service];
    requireSafe(Object.keys(security.tmpfs||{}).sort().join(',')===[...destinations].sort().join(','));
    for(const mount of m.mounts) requireSafe((mount.Type==='tmpfs'&&destinations.includes(mount.Destination))||(mount.Type==='bind'&&service==='web'&&mount.Destination==='/ops'&&!mount.RW&&sourceAlias(mount.Source,__dirname)));
  }
  const network=JSON.parse(docker(['network','inspect','--format','{{json .}}',receipt.networkId]));
  requireSafe(network.Internal&&network.Labels['com.docker.compose.project']===receipt.project);
  requireSafe(Object.keys(network.Containers||{}).every(id=>Object.values(receipt.services).includes(id)));
  return true;
}
function createRuntime(role) {
  requireSafe(['synthetic-source','synthetic-target','original-target'].includes(role));
  const run=crypto.randomBytes(8).toString('hex'),project=`classifieds-rebuild-recovery-${run}-${role}`;
  const receipt={run,role,project,services:{},images:{},status:'creating'};
  const file=path.join(docs,`runtime-${run}.json`);let fileCreated=false;
  const owner={token:crypto.randomBytes(16).toString('hex'),attempted:false,known:[],removed:[],unknown:false,expectedImages:{}};
  owners.set(receipt,owner);
  const env={...process.env,COMPOSE_DISABLE_ENV_FILE:'1',RECOVERY_RUN:run,RECOVERY_ROLE:role,RECOVERY_OPS_ROOT:__dirname,
    RECOVERY_ATTEMPT:owner.token,RECOVERY_DB_PASSWORD:crypto.randomBytes(32).toString('hex'),RECOVERY_BOOT_KEY:crypto.randomBytes(48).toString('hex')};
  const args=['compose','--env-file','NUL','-f',path.join(__dirname,'compose.recovery.yaml'),'-p',project];
  try {
    mustPersist(fs,file,receipt,true);fileCreated=true;
    owner.beforeContainers=docker(['ps','-aq','--no-trunc']).split(/\r?\n/).filter(Boolean);
    owner.beforeNetworks=docker(['network','ls','-q','--no-trunc']).split(/\r?\n/).filter(Boolean);
    for(const [service,ref]of Object.entries(imageRefs))owner.expectedImages[service]=docker(['image','inspect','--format','{{.Id}}',ref]);
    requireSafe(!docker(['ps','-aq','--filter',`label=com.docker.compose.project=${project}`]));
    requireSafe(!docker(['network','ls','-q','--filter',`label=com.docker.compose.project=${project}`]));
    owner.attempted=true;
    try {execFileSync('docker',[...args,'up','-d','--no-build','--pull','never','--wait','--wait-timeout','90'],{env,windowsHide:true,stdio:['ignore','pipe','pipe'],timeout:120000});}
    catch {throw new Error('runtime_start_failed');}
    discover(receipt,owner);
    requireSafe(!owner.unknown,'runtime_discovery_failed');
    for(const id of owner.containers)guardCleanupContainer(id,receipt,owner);
    const createdNetwork=JSON.parse(docker(['network','inspect','--format','{{json .}}',receipt.networkId]));
    ownership(createdNetwork.Labels,receipt,owner);
    requireSafe(createdNetwork.Id===receipt.networkId&&!owner.beforeNetworks.includes(receipt.networkId),'identity_refused');
    receipt.status='created_unverified';mustPersist(fs,file,receipt);
    validateOwned(receipt);receipt.status='guarded';mustPersist(fs,file,receipt);
    owner.transferred=true;return receipt;
  } catch(error){
    const primary=failure(error,'runtime_prepare_failed');
    if(owner.attempted&&!owner.discovered)discover(receipt,owner);
    try{stopOwnedRuntime(receipt);}catch{}
    receipt.status='constructor_failed';receipt.resources=resourceState(receipt,owner);
    const saved=fileCreated?persist(fs,file,receipt):'write_failed';if(saved==='write_failed')receipt.resources.persistence=saved;
    throw failure(primary,'runtime_prepare_failed',receipt.resources);
  } finally {
    delete env.RECOVERY_DB_PASSWORD;delete env.RECOVERY_BOOT_KEY;delete env.RECOVERY_ATTEMPT;
  }
}
function discover(receipt,owner){
  owner.discovered=true;
  try{
    const containers=docker(['ps','-aq','--no-trunc','--filter',`label=com.docker.compose.project=${receipt.project}`]).split(/\r?\n/).filter(Boolean);
    owner.known=[...containers];owner.containers=containers;
    const networks=docker(['network','ls','-q','--no-trunc','--filter',`label=com.docker.compose.project=${receipt.project}`]).split(/\r?\n/).filter(Boolean);
    requireSafe(containers.length<=3&&networks.length<=1,'runtime_discovery_failed');
    owner.known=[...new Set([...containers,...networks])];owner.containers=containers;owner.networks=networks;
    for(const id of containers)try{const m=metadata(id),service=m.labels?.['com.docker.compose.service'];requireSafe(Object.hasOwn(imageRefs,service)&&!receipt.services[service]);receipt.services[service]=id;receipt.images[service]=m.image;}catch{owner.unknown=true;}
    receipt.networkId=networks[0];
  }catch{owner.unknown=true;}
}
function resourceState(receipt,owner){return safeResources({run:receipt.run,role:receipt.role,known:owner.known,removed:owner.removed,retained:owner.known.filter(id=>!owner.removed.includes(id)),unknown:owner.unknown,status:owner.unknown||owner.known.some(id=>!owner.removed.includes(id))?'cleanup_blocked':owner.attempted?'removed':'not_created',persistence:owner.persistence||'not_attempted'});}
function ownership(labels,receipt,owner){requireSafe(labels?.['phase15.run']===receipt.run&&labels['phase15.role']===receipt.role&&labels['phase15.attempt']===owner.token&&labels['com.docker.compose.project']===receipt.project,'cleanup_blocked');}
function guardCleanupContainer(id,receipt,owner){
 const baseline=JSON.parse(fs.readFileSync(path.join(docs,'baseline.json')));
 requireSafe(/^[a-f0-9]{64}$/.test(id)&&!baseline.containerIds.includes(id)&&!owner.beforeContainers.includes(id),'cleanup_blocked');
 const m=metadata(id),service=m.labels?.['com.docker.compose.service'];ownership(m.labels,receipt,owner);
 requireSafe(Object.hasOwn(imageRefs,service)&&m.id===id&&m.image===owner.expectedImages[service],'cleanup_blocked');
 const s=JSON.parse(docker(['inspect','--format','{"imageRef":{{json .Config.Image}},"capDrop":{{json .HostConfig.CapDrop}},"securityOpt":{{json .HostConfig.SecurityOpt}},"tmpfs":{{json .HostConfig.Tmpfs}}}',id]));
 requireSafe(s.imageRef===imageRefs[service]&&s.capDrop?.includes('ALL')&&s.securityOpt?.some(x=>['no-new-privileges','no-new-privileges:true'].includes(x))&&m.readonly&&!m.privileged&&!(m.capAdd||[]).length&&!Object.keys(m.ports||{}).length,'cleanup_blocked');
 const destinations={web:['/var/lib/classifieds/media','/run','/tmp'],db:['/var/lib/postgresql/data','/var/run/postgresql','/tmp'],redis:['/data']}[service];
 requireSafe(Object.keys(s.tmpfs||{}).sort().join(',')===[...destinations].sort().join(','),'cleanup_blocked');
 for(const mount of m.mounts)requireSafe((mount.Type==='tmpfs'&&destinations.includes(mount.Destination))||(mount.Type==='bind'&&service==='web'&&mount.Destination==='/ops'&&!mount.RW&&sourceAlias(mount.Source,__dirname)),'cleanup_blocked');
 requireSafe(Object.values(m.networks).every(n=>!n.NetworkID||(owner.networks.includes(n.NetworkID)&&!baseline.networkIds.includes(n.NetworkID))),'cleanup_blocked');
}
function guardCleanupNetwork(id,receipt,owner){
 const baseline=JSON.parse(fs.readFileSync(path.join(docs,'baseline.json')));
 requireSafe(/^[a-f0-9]{64}$/.test(id)&&!baseline.networkIds.includes(id)&&!owner.beforeNetworks.includes(id),'cleanup_blocked');
 const n=JSON.parse(docker(['network','inspect','--format','{{json .}}',id]));ownership(n.Labels,receipt,owner);
 requireSafe(n.Id===id&&n.Internal&&n.Labels['com.docker.compose.network']==='default'&&Object.keys(n.Containers||{}).length===0,'cleanup_blocked');
}
function inspectSource(receipt) {
  validateOwned(receipt);requireSafe(receipt.role==='synthetic-source');
  return {appId:receipt.services.web,dbId:receipt.services.db,image,manifest};
}
function stopOwnedRuntime(receipt) {
  const owner=owners.get(receipt);requireSafe(owner,'cleanup_blocked');
  if(!owner.cleaned){
    for(const id of owner.containers||[])try{guardCleanupContainer(id,receipt,owner);require('./graceful.cjs').gracefulStop(docker,id);requireSafe(['exited','created'].includes(metadata(id).state),'cleanup_blocked');docker(['rm',id]);owner.removed.push(id);}catch{}
    for(const id of owner.networks||[])try{guardCleanupNetwork(id,receipt,owner);docker(['network','rm',id]);owner.removed.push(id);}catch{}
    owner.cleaned=true;
    const state=resourceState(receipt,owner);
    owner.persistence=persist(fs,path.join(docs,`cleanup-${receipt.run}.json`),state,true);
  }
  const resources=resourceState(receipt,owner);
  if(resources.status==='cleanup_blocked'||resources.persistence==='write_failed')throw Object.assign(Error(resources.status==='cleanup_blocked'?'cleanup_blocked':'receipt_write_failed'),{resources});
  return {run:receipt.run,removedContainers:(owner.containers||[]).filter(id=>owner.removed.includes(id)).length,removedNetwork:(owner.networks||[]).length>0&&(owner.networks||[]).every(id=>owner.removed.includes(id)),resources};
}
module.exports={createRuntime,validateOwned,inspectSource,metadata,stopOwnedRuntime};

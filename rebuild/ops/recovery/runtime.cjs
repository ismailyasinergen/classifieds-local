'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const {command,image,manifest,developer}=require('./inspect.cjs');
const {requireSafe}=require('./guards.cjs');
const docs=path.join(developer,'rebuild/docs/phase7');
const docker=args=>command('docker',args);
const imageRefs={web:image,db:'postgres:17.11-bookworm@sha256:3645570cccdfa447589da9f57dd740faa29b30938e861289a5574b6ca6b03826',redis:'redis:7.4.11-bookworm@sha256:4fa24486b8bcca8eec45ee0eb166edc674795e53a2b53d1a9ef263eecebaac85'};
const metadata=id=>JSON.parse(docker(['inspect','--format','{"id":{{json .Id}},"image":{{json .Image}},"labels":{{json .Config.Labels}},"mounts":{{json .Mounts}},"ports":{{json .HostConfig.PortBindings}},"networks":{{json .NetworkSettings.Networks}},"privileged":{{json .HostConfig.Privileged}},"capAdd":{{json .HostConfig.CapAdd}},"readonly":{{json .HostConfig.ReadonlyRootfs}},"state":{{json .State.Status}}}',id]));
function validateOwned(receipt) {
  requireSafe(/^[a-f0-9]{16}$/.test(receipt.run)&&['synthetic-source','synthetic-target','original-target'].includes(receipt.role));
  requireSafe(receipt.project===`classifieds-rebuild-recovery-${receipt.run}-${receipt.role}`);
  requireSafe(Object.keys(receipt.services).sort().join(',')==='db,redis,web');
  const baseline=JSON.parse(fs.readFileSync(path.join(docs,'runtime-baseline.json')));
  for(const [service,id] of Object.entries(receipt.services)) {
    requireSafe(/^[a-f0-9]{64}$/.test(id)&&!baseline.containerIds.includes(id));
    const m=metadata(id);
    const security=JSON.parse(docker(['inspect','--format','{"imageRef":{{json .Config.Image}},"capDrop":{{json .HostConfig.CapDrop}},"securityOpt":{{json .HostConfig.SecurityOpt}},"tmpfs":{{json .HostConfig.Tmpfs}}}',id]));
    requireSafe(security.imageRef===imageRefs[service]&&security.capDrop?.includes('ALL')&&security.securityOpt?.some(s=>s==='no-new-privileges:true'||s==='no-new-privileges'));
    requireSafe(m.labels['com.docker.compose.project']===receipt.project&&m.labels['com.docker.compose.service']===service);
    requireSafe(m.image===receipt.images[service]&&(service!=='web'||m.image===image));
    requireSafe(m.readonly&&!m.privileged&&!(m.capAdd||[]).length&&!Object.keys(m.ports||{}).length);
    requireSafe(Object.values(m.networks).length===1&&Object.values(m.networks)[0].NetworkID===receipt.networkId&&!baseline.networkIds.includes(receipt.networkId));
    const destinations={web:['/var/lib/classifieds/media','/run','/tmp'],db:['/var/lib/postgresql/data','/var/run/postgresql','/tmp'],redis:['/data']}[service];
    requireSafe(Object.keys(security.tmpfs||{}).sort().join(',')===[...destinations].sort().join(','));
    for(const mount of m.mounts) requireSafe((mount.Type==='tmpfs'&&destinations.includes(mount.Destination))||(mount.Type==='bind'&&service==='web'&&mount.Destination==='/ops'&&!mount.RW&&path.resolve(mount.Source)===path.resolve(__dirname)));
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
  const file=path.join(docs,`runtime-${run}.json`);fs.writeFileSync(file,JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
  const env={...process.env,COMPOSE_DISABLE_ENV_FILE:'1',RECOVERY_RUN:run,RECOVERY_ROLE:role,RECOVERY_OPS_ROOT:__dirname,
    RECOVERY_DB_PASSWORD:crypto.randomBytes(32).toString('hex'),RECOVERY_BOOT_KEY:crypto.randomBytes(48).toString('hex')};
  const args=['compose','--env-file','NUL','-f',path.join(__dirname,'compose.recovery.yaml'),'-p',project];
  try {
    requireSafe(!docker(['ps','-aq','--filter',`label=com.docker.compose.project=${project}`]));
    try {execFileSync('docker',[...args,'up','-d','--no-build','--pull','never','--wait','--wait-timeout','90'],{env,windowsHide:true,stdio:['ignore','pipe','pipe'],timeout:120000});}
    catch {throw new Error('runtime_start_failed');}
  } finally {
    delete env.RECOVERY_DB_PASSWORD;delete env.RECOVERY_BOOT_KEY;
    for(const id of docker(['ps','-aq','--no-trunc','--filter',`label=com.docker.compose.project=${project}`]).split(/\r?\n/).filter(Boolean)) {
      const m=metadata(id),service=m.labels['com.docker.compose.service'];
      requireSafe(['web','db','redis'].includes(service)&&!receipt.services[service]);
      receipt.services[service]=id;receipt.images[service]=m.image;
      receipt.networkId=Object.values(m.networks)[0]?.NetworkID;
    }
    receipt.status='created_unverified';fs.writeFileSync(file,JSON.stringify(receipt,null,2)+'\n');
  }
  validateOwned(receipt);receipt.status='guarded';fs.writeFileSync(file,JSON.stringify(receipt,null,2)+'\n');return receipt;
}
function inspectSource(receipt) {
  validateOwned(receipt);requireSafe(receipt.role==='synthetic-source');
  return {appId:receipt.services.web,dbId:receipt.services.db,image,manifest};
}
function stopOwnedRuntime(receipt) {
  validateOwned(receipt);
  const ids=Object.values(receipt.services);
  docker(['stop','--time','10',...ids]);
  for(const id of ids)requireSafe(metadata(id).state==='exited');
  docker(['rm',...ids]);
  const net=JSON.parse(docker(['network','inspect','--format','{{json .}}',receipt.networkId]));
  requireSafe(net.Labels['com.docker.compose.project']===receipt.project&&Object.keys(net.Containers||{}).length===0);
  docker(['network','rm',receipt.networkId]);
  const result={...receipt,status:'stopped_removed',removedAt:new Date().toISOString()};
  fs.writeFileSync(path.join(docs,`cleanup-${receipt.run}.json`),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  return {run:receipt.run,removedContainers:ids.length,removedNetwork:true};
}
module.exports={createRuntime,validateOwned,inspectSource,metadata,stopOwnedRuntime};

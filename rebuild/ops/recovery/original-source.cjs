'use strict';
const path=require('node:path');
const {requireSafe}=require('./guards.cjs');
const {image,manifest,original}=require('./inspect.cjs');
const fs=require('node:fs'),crypto=require('node:crypto');
const {command,verifySources,developer,hash}=require('./inspect.cjs');
const {privateRun}=require('./capture.cjs');
const orderedMounts=mounts=>[...mounts].sort((a,b)=>a.Destination.localeCompare(b.Destination));
function isOpsMount(source){
  const desktop='/run/desktop/mnt/host/'+__dirname[0].toLowerCase()+__dirname.slice(2).replaceAll('\\','/');
  return source===desktop||path.resolve(source)===path.resolve(__dirname);
}
function guardOriginal(current,expected) {
  const ok=current.manifest===manifest&&expected.manifest===manifest&&
    current.app.image===image&&current.app.state==='running'&&current.db.state==='running'&&
    ['app','db'].every(k=>/^[a-f0-9]{64}$/.test(current[k].id)&&current[k].project==='classifieds-rebuild'&&
      ['id','image','configHash','service','networks'].every(f=>JSON.stringify(current[k][f])===JSON.stringify(expected[k][f])))&&
    current.app.service==='web'&&current.db.service==='db'&&current.app.id!==current.db.id&&
    current.app.networks.length===1&&JSON.stringify(current.app.networks)===JSON.stringify(current.db.networks)&&
    JSON.stringify(orderedMounts(current.app.mounts))===JSON.stringify(orderedMounts(expected.app.mounts))&&
    current.app.mounts.some(m=>m.Type==='bind'&&!m.RW&&m.Destination==='/app'&&path.resolve(m.Source)===path.resolve(original,'rebuild/backend'))&&
    current.app.mounts.some(m=>m.Type==='volume'&&m.Name==='classifieds-rebuild_rebuild_media'&&m.Destination==='/var/lib/classifieds/media');
  requireSafe(ok,'original_identity_refused');return true;
}
function memoryCommand(appId,mode,{dbIp,dbBinding}) {
  requireSafe(/^[a-f0-9]{64}$/.test(appId)&&['snapshot','keys','key-identity'].includes(mode)&&
    /^(\d{1,3}\.){3}\d{1,3}$/.test(dbIp)&&/^[a-f0-9]{64}$/.test(dbBinding),'original_transport_refused');
  const fs=require('node:fs');
  const catalog=fs.readFileSync(path.join(__dirname,'snapshot_catalog.py'),'utf8');
  const main=fs.readFileSync(path.join(__dirname,'original_export.py'),'utf8');
  const code=`import sys,types\nm=types.ModuleType('snapshot_catalog')\nsys.modules['snapshot_catalog']=m\nexec(${JSON.stringify(catalog)},m.__dict__)\n`+main;
  return {command:'docker',args:['exec','-i','-e','PGOPTIONS=-c default_transaction_read_only=on -c statement_timeout=300000 -c lock_timeout=5000',
    appId,'python','-B','-c',code,mode,dbIp,dbBinding]};
}
const docker=args=>command('docker',args);
const boundSources=new WeakSet();
const ownerProbe="import os,stat,json\nr=[]\nfor p in ['/var/lib/classifieds/media','/var/lib/classifieds/media/originals','/var/lib/classifieds/media/derivatives']:\n s=os.lstat(p);r.append({'uid':s.st_uid,'gid':s.st_gid,'mode':stat.S_IMODE(s.st_mode),'directory':stat.S_ISDIR(s.st_mode)})\nprint(json.dumps({'uid':os.getuid(),'gid':os.getgid(),'uidMap':open('/proc/self/uid_map').read().split(),'gidMap':open('/proc/self/gid_map').read().split(),'directories':r}))";
function sourceMetadata(id) {
  const m=JSON.parse(docker(['inspect','--format','{"id":{{json .Id}},"image":{{json .Image}},"state":{{json .State.Status}},"labels":{{json .Config.Labels}},"mounts":{{json .Mounts}},"nets":{{json .NetworkSettings.Networks}}}',id]));
  return {id:m.id,image:m.image,state:m.state,project:m.labels['com.docker.compose.project'],service:m.labels['com.docker.compose.service'],
    configHash:m.labels['com.docker.compose.config-hash'],mounts:orderedMounts(m.mounts),networks:Object.values(m.nets).map(n=>n.NetworkID),ips:Object.values(m.nets).map(n=>n.IPAddress)};
}
function bindOriginal(baseline) {
  verifySources();
  const records=['web','db'].map(service=>baseline.runtime.find(r=>r.project==='classifieds-rebuild'&&r.service===service));
  requireSafe(records.every(Boolean),'original_identity_refused');
  const [app,db]=records.map(r=>sourceMetadata(r.id));
  for(const [index,m] of [app,db].entries()) {
    const r=records[index];
    requireSafe(m.id===r.id&&m.image===r.image&&m.configHash===r.configHash&&JSON.stringify(m.networks)===JSON.stringify(r.networkIds),'original_identity_refused');
  }
  const expected={app,db,manifest};guardOriginal(expected,expected);
  const run=crypto.randomBytes(8).toString('hex');
  const inspect=()=>{
    const current={app:sourceMetadata(app.id),db:sourceMetadata(db.id),manifest};guardOriginal(current,expected);
    requireSafe(JSON.stringify(current)===JSON.stringify(expected),'original_identity_changed');
    return {appId:app.id,dbId:db.id,image,manifest};
  };
  inspect();
  // Only database/user identifiers flow through this private pipe; no environment dump.
  const binding=privateRun({command:'docker',args:['exec',db.id,'sh','-c','printf "%s\\n%s" "$POSTGRES_DB" "$POSTGRES_USER"']},4096);
  const context={dbIp:db.ips[0],dbBinding:hash(binding)};binding.fill(0);
  const source={run,appId:app.id,dbId:db.id,expected,inspect,
    sourceCommand(mode){inspect();return memoryCommand(app.id,mode,context);}};
  boundSources.add(source);return source;
}
function createMediaReader(run,volume='classifieds-rebuild_rebuild_media') {
  return createReader(run,volume,'nonroot',()=>{});
}
function createOriginalMediaReader(source){
  requireSafe(boundSources.has(source),'media_owner_refused');
  require('./task6-gate.cjs').verifyReview();
  const ownership=()=>{source.inspect();guardOwnerMetadata(JSON.parse(docker(['exec',source.appId,'python','-B','-c',ownerProbe])));};
  ownership();
  return createReader(source.run,'classifieds-rebuild_rebuild_media','original-owner',ownership);
}
function createReader(run,volume,profile,ownership) {
  requireSafe(/^[a-f0-9]{16}$/.test(run)&&volume==='classifieds-rebuild_rebuild_media','media_reader_refused');
  const name=`classifieds-rebuild-recovery-${run}-media-reader`;
  const id=docker(['create','--name',name,'--label',`phase7.run=${run}`,'--network','none','--read-only','--cap-drop','ALL',
    '--security-opt','no-new-privileges','--user',profile==='original-owner'?'0:0':'1000:1000','--mount',`type=volume,source=${volume},target=/media,readonly`,
    '--mount',`type=bind,source=${__dirname},target=/ops,readonly`,image,'sleep','900']);
  const receipt={run,id,name,volume,image,profile,status:'created'};
  const file=path.join(developer,'rebuild/docs/phase7',`media-reader-${run}.json`);
  fs.writeFileSync(file,JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
  const inspect=()=>{
    requireSafe(/^[a-f0-9]{64}$/.test(id),'media_reader_refused');
    const m=JSON.parse(docker(['inspect','--format',readerFormat,id]));
    guardReader(m,receipt);
  };
  const preflight=()=>{ownership();inspect();docker(['exec',id,'python','-B','/ops/reader_preflight.py',profile]);};
  try {inspect();docker(['start',id]);preflight();receipt.status='running';}
  catch {
    receipt.status='constructor_failed';receipt.cleanup='retained_exact_id';
    try{inspect();docker(['stop','--time','5',id]);docker(['rm',id]);receipt.cleanup='removed_exact_id';}catch{receipt.cleanup='cleanup_blocked';}
    fs.writeFileSync(file,JSON.stringify(receipt,null,2)+'\n');throw Object.assign(Error('media_reader_constructor_failed'),{mediaReader:receipt});
  }
  fs.writeFileSync(file,JSON.stringify(receipt,null,2)+'\n');
  return {receipt,command(mode,data){preflight();requireSafe(['inventory','stream'].includes(mode),'media_reader_refused');
    return {command:'docker',args:['exec','-i',id,'python','-B','/ops/original_media.py',mode],input:Buffer.from(JSON.stringify(data))};},
    close(){inspect();docker(['stop','--time','5',id]);docker(['rm',id]);receipt.status='removed';fs.writeFileSync(file,JSON.stringify(receipt,null,2)+'\n');}};
}
function guardOwnerMetadata(m){
  requireSafe(m?.uid===0&&m.gid===0&&['uidMap','gidMap'].every(k=>JSON.stringify(m[k])==='["0","0","4294967295"]')&&
    m.directories?.length===3&&m.directories.every((d,i)=>d.uid===0&&d.gid===0&&d.directory===true&&d.mode===(i===0?493:448)),'media_owner_refused');return true;
}
const readerFormat='{"id":{{json .Id}},"image":{{json .Image}},"labels":{{json .Config.Labels}},"user":{{json .Config.User}},"mounts":{{json .Mounts}},"network":{{json .HostConfig.NetworkMode}},"ports":{{json .HostConfig.PortBindings}},"readonly":{{json .HostConfig.ReadonlyRootfs}},"privileged":{{json .HostConfig.Privileged}},"capAdd":{{json .HostConfig.CapAdd}},"capDrop":{{json .HostConfig.CapDrop}},"security":{{json .HostConfig.SecurityOpt}},"pid":{{json .HostConfig.PidMode}},"userns":{{json .HostConfig.UsernsMode}},"ipc":{{json .HostConfig.IpcMode}}}';
function guardReader(m,r){
  requireSafe(['nonroot','original-owner'].includes(r.profile)&&m.id===r.id&&m.image===image&&m.labels?.['phase7.run']===r.run&&
    m.user===(r.profile==='original-owner'?'0:0':'1000:1000')&&m.network==='none'&&m.readonly===true&&m.privileged===false&&
    !(m.capAdd||[]).length&&JSON.stringify(m.capDrop)==='["ALL"]'&&JSON.stringify(m.security)==='["no-new-privileges"]'&&
    !Object.keys(m.ports||{}).length&&m.pid===''&&m.userns===''&&m.ipc==='private'&&m.mounts?.length===2&&
    m.mounts.filter(m=>m.Type==='volume'&&m.Name===r.volume&&m.Destination==='/media'&&m.RW===false).length===1&&
    m.mounts.filter(m=>m.Type==='bind'&&isOpsMount(m.Source)&&m.Destination==='/ops'&&m.RW===false).length===1,'media_reader_refused');return true;
}
module.exports={guardOriginal,memoryCommand,bindOriginal,createMediaReader,createOriginalMediaReader,isOpsMount,guardOwnerMetadata,guardReader,readerFormat};
